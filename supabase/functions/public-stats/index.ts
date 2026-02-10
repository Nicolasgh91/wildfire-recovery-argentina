import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CACHE_TTL = 3600;
const STALE_REVALIDATE = 600;
const STALE_IF_ERROR = 86400;
const RATE_LIMIT_PER_MIN = 100;
const API_VERSION = "1";
const MAX_RANGE_DAYS = 730;
const MS_PER_DAY = 24 * 60 * 60 * 1000;
const ALLOWED_ORIGINS = (Deno.env.get("ALLOWED_ORIGINS") ?? "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const ipRequests = new Map<string, { count: number; resetAt: number }>();

function checkRateLimit(ip: string): {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAt: number;
} {
  const now = Date.now();
  let record = ipRequests.get(ip);
  if (!record || record.resetAt < now) {
    record = { count: 0, resetAt: now + 60000 };
    ipRequests.set(ip, record);
  }
  if (record.count >= RATE_LIMIT_PER_MIN) {
    return {
      allowed: false,
      limit: RATE_LIMIT_PER_MIN,
      remaining: 0,
      resetAt: record.resetAt,
    };
  }
  record.count++;
  return {
    allowed: true,
    limit: RATE_LIMIT_PER_MIN,
    remaining: Math.max(0, RATE_LIMIT_PER_MIN - record.count),
    resetAt: record.resetAt,
  };
}

function parseIsoDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
    return null;
  }
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return date;
}

function getCorsHeaders(req: Request): Record<string, string> {
  if (ALLOWED_ORIGINS.length === 0) {
    return { "Access-Control-Allow-Origin": "*" };
  }
  const origin = req.headers.get("origin");
  if (!origin) {
    return { "Access-Control-Allow-Origin": "*" };
  }
  if (ALLOWED_ORIGINS.includes(origin)) {
    return { "Access-Control-Allow-Origin": origin, Vary: "Origin" };
  }
  return {};
}

function jsonResponse(
  status: number,
  body: unknown,
  headers: HeadersInit = {},
  corsHeaders: HeadersInit = {},
) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders, ...headers },
  });
}

serve(async (req) => {
  const corsHeaders = getCorsHeaders(req);
  const origin = req.headers.get("origin");
  if (ALLOWED_ORIGINS.length > 0 && origin && Object.keys(corsHeaders).length === 0) {
    return jsonResponse(403, { error: "Origin not allowed" });
  }

  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        ...corsHeaders,
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "content-type",
        "Access-Control-Max-Age": "86400",
      },
    });
  }

  if (req.method !== "GET") {
    return jsonResponse(405, { error: "Method not allowed" }, {}, corsHeaders);
  }

  const ip = (req.headers.get("x-forwarded-for") || req.headers.get("x-real-ip") || "unknown")
    .split(",")[0]
    .trim();
  const rate = checkRateLimit(ip);
  const rateHeaders = {
    "X-RateLimit-Limit": String(rate.limit),
    "X-RateLimit-Remaining": String(rate.remaining),
    "X-RateLimit-Reset": String(Math.ceil(rate.resetAt / 1000)),
  };
  if (!rate.allowed) {
    return jsonResponse(429, { error: "Rate limit exceeded" }, rateHeaders, corsHeaders);
  }

  const url = new URL(req.url);
  const version = url.searchParams.get("v") || API_VERSION;
  if (version !== API_VERSION) {
    return jsonResponse(400, { error: "Unsupported API version" }, rateHeaders, corsHeaders);
  }

  const dateFrom = url.searchParams.get("date_from");
  const dateTo = url.searchParams.get("date_to");
  const province = url.searchParams.get("province")?.trim() || null;

  if (!dateFrom || !dateTo) {
    return jsonResponse(400, { error: "date_from and date_to are required" }, rateHeaders, corsHeaders);
  }

  const fromDate = parseIsoDate(dateFrom);
  const toDate = parseIsoDate(dateTo);
  if (!fromDate || !toDate) {
    return jsonResponse(400, { error: "Invalid date format (YYYY-MM-DD)" }, rateHeaders, corsHeaders);
  }
  const diffDays = Math.floor((toDate.getTime() - fromDate.getTime()) / MS_PER_DAY);
  if (diffDays < 0) {
    return jsonResponse(400, { error: "date_to must be >= date_from" }, rateHeaders, corsHeaders);
  }
  if (diffDays > MAX_RANGE_DAYS) {
    return jsonResponse(400, { error: "Date range cannot exceed 730 days" }, rateHeaders, corsHeaders);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const supabaseKey = Deno.env.get("SUPABASE_ANON_KEY");
  if (!supabaseUrl || !supabaseKey) {
    return jsonResponse(500, { error: "Missing Supabase configuration" }, rateHeaders, corsHeaders);
  }

  const supabase = createClient(supabaseUrl, supabaseKey, {
    db: { schema: "api" },
  });
  const { data, error } = await supabase.rpc("get_public_stats", {
    p_date_from: dateFrom,
    p_date_to: dateTo,
    p_province: province,
  });

  if (error) {
    const status = error.code === "P0001" ? 400 : 500;
    if (status === 500) {
      console.error("public-stats rpc error:", error);
      return jsonResponse(500, { error: "Internal server error" }, rateHeaders, corsHeaders);
    }
    return jsonResponse(status, { error: error.message }, rateHeaders, corsHeaders);
  }

  return jsonResponse(
    200,
    { version: API_VERSION, data },
    {
      "Cache-Control": `public, s-maxage=${CACHE_TTL}, stale-while-revalidate=${STALE_REVALIDATE}, stale-if-error=${STALE_IF_ERROR}`,
      "X-API-Version": API_VERSION,
      ...rateHeaders,
    },
    corsHeaders,
  );
});
