param(
  [Parameter(Mandatory = $false)]
  [string]$Url = $env:PUBLIC_STATS_URL,
  [Parameter(Mandatory = $false)]
  [string]$Origin,
  [Parameter(Mandatory = $false)]
  [string]$AnonKey = $env:SUPABASE_ANON_KEY,
  [Parameter(Mandatory = $false)]
  [string]$AccessToken = $env:SUPABASE_ACCESS_TOKEN,
  [Parameter(Mandatory = $false)]
  [bool]$RateLimitTest = $true,
  [Parameter(Mandatory = $false)]
  [int]$RateLimitRequests = 120
)

if (-not $Url) {
  Write-Error "Missing URL. Set PUBLIC_STATS_URL or pass -Url."
  exit 1
}

$Url = $Url.Trim()
if (
  ($Url.StartsWith('"') -and $Url.EndsWith('"')) -or
  ($Url.StartsWith("'") -and $Url.EndsWith("'"))
) {
  $Url = $Url.Substring(1, $Url.Length - 2).Trim()
}

if (-not [Uri]::TryCreate($Url, [UriKind]::Absolute, [ref]$null)) {
  Write-Error "Invalid URL: '$Url'"
  if ($Url -match "\s") {
    Write-Warning "URL contains whitespace. Remove spaces/newlines."
  }
  exit 1
}

Write-Output "Using URL: $Url"

if (-not $AnonKey) {
  $envPath = Join-Path $PSScriptRoot "..\\.env"
  if (Test-Path $envPath) {
    foreach ($line in Get-Content $envPath) {
      $trimmed = $line.Trim()
      if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
      $idx = $trimmed.IndexOf("=")
      if ($idx -lt 1) { continue }
      $key = $trimmed.Substring(0, $idx).Trim()
      $val = $trimmed.Substring($idx + 1).Trim()
      if (
        $key -eq "SUPABASE_ANON_KEY" -or
        $key -eq "VITE_SUPABASE_ANON_KEY" -or
        $key -eq "ANON_KEY"
      ) {
        if (
          ($val.StartsWith('"') -and $val.EndsWith('"')) -or
          ($val.StartsWith("'") -and $val.EndsWith("'"))
        ) {
          $val = $val.Substring(1, $val.Length - 2).Trim()
        }
        if ($val) {
          $AnonKey = $val
          break
        }
      }
    }
  }
}

$authToken = $AccessToken
if (-not $authToken) {
  $authToken = $AnonKey
}

function Invoke-Http([string]$RequestUrl, [hashtable]$Headers = @{}) {
  if (-not [Uri]::TryCreate($RequestUrl, [UriKind]::Absolute, [ref]$null)) {
    Write-Error "Invalid request URL: '$RequestUrl'"
    if ($RequestUrl -match "\s") {
      Write-Warning "Request URL contains whitespace. Remove spaces/newlines."
    }
    throw "Invalid request URL"
  }
  try {
    $resp = Invoke-WebRequest -Uri $RequestUrl -Headers $Headers -UseBasicParsing
    return @{
      Status  = [int]$resp.StatusCode
      Body    = $resp.Content
      Headers = $resp.Headers
    }
  } catch {
    $webResp = $_.Exception.Response
    if ($null -ne $webResp) {
      $status = [int]$webResp.StatusCode
      $reader = New-Object System.IO.StreamReader($webResp.GetResponseStream())
      $body = $reader.ReadToEnd()
      $reader.Close()
      return @{
        Status  = $status
        Body    = $body
        Headers = $webResp.Headers
      }
    }
    throw
  }
}

function Assert-True([bool]$Condition, [string]$Message) {
  if (-not $Condition) {
    Write-Error $Message
    $script:failed = $true
  } else {
    Write-Output "OK: $Message"
  }
}

function Assert-Equal($Actual, $Expected, [string]$Message) {
  Assert-True ($Actual -eq $Expected) "$Message (actual=$Actual expected=$Expected)"
}

function Build-Url([string]$Base, [hashtable]$Query) {
  $builder = [System.UriBuilder]::new($Base)
  $pairs = @()
  foreach ($key in $Query.Keys) {
    $pairs += ("{0}={1}" -f $key, [uri]::EscapeDataString([string]$Query[$key]))
  }
  $existing = $builder.Query.TrimStart("?")
  if ($existing) {
    $builder.Query = "$existing&$([string]::Join('&', $pairs))"
  } else {
    $builder.Query = [string]::Join('&', $pairs)
  }
  return $builder.Uri.AbsoluteUri
}

$script:failed = $false
$baseHeaders = @{}
if ($Origin) {
  $baseHeaders["Origin"] = $Origin
}
if ($authToken) {
  $baseHeaders["Authorization"] = "Bearer $authToken"
  Write-Output "Authorization header: set"
} else {
  Write-Warning "Authorization header not set. If Verify JWT is enabled, expect 401."
}
if ($AnonKey) {
  $baseHeaders["apikey"] = $AnonKey
  Write-Output "apikey header: set"
} elseif ($AccessToken) {
  $baseHeaders["apikey"] = $AccessToken
  Write-Warning "apikey set to access token (anon key not found). Prefer anon key."
}

$okUrl = Build-Url $Url @{
  v = "1"
  date_from = "2024-01-01"
  date_to   = "2024-01-15"
}
$resp = Invoke-Http $okUrl $baseHeaders
Assert-Equal $resp.Status 200 "GET valid range returns 200"
Assert-True ($resp.Headers["Cache-Control"] -match "s-maxage=3600") "Cache-Control has s-maxage=3600"
Assert-True ($resp.Headers["Cache-Control"] -match "stale-while-revalidate=600") "Cache-Control has stale-while-revalidate=600"
Assert-True ($resp.Headers["Cache-Control"] -match "stale-if-error=86400") "Cache-Control has stale-if-error=86400"
Assert-Equal $resp.Headers["X-API-Version"] "1" "X-API-Version is 1"
Assert-True ($resp.Headers["X-RateLimit-Limit"] -ne $null) "X-RateLimit-Limit present"
Assert-True ($resp.Headers["X-RateLimit-Remaining"] -ne $null) "X-RateLimit-Remaining present"
Assert-True ($resp.Headers["X-RateLimit-Reset"] -ne $null) "X-RateLimit-Reset present"
if ($Origin) {
  Assert-True ($resp.Headers["Access-Control-Allow-Origin"] -ne $null) "CORS header present"
}

$invalidOrderUrl = Build-Url $Url @{
  v = "1"
  date_from = "2024-02-01"
  date_to   = "2024-01-01"
}
$resp = Invoke-Http $invalidOrderUrl $baseHeaders
Assert-Equal $resp.Status 400 "date_to < date_from returns 400"

$rangeTooBigUrl = Build-Url $Url @{
  v = "1"
  date_from = "2020-01-01"
  date_to   = "2024-12-31"
}
$resp = Invoke-Http $rangeTooBigUrl $baseHeaders
Assert-Equal $resp.Status 400 "range > 730 days returns 400"

$badFormatUrl = Build-Url $Url @{
  v = "1"
  date_from = "2024-13-40"
  date_to   = "2024-01-01"
}
$resp = Invoke-Http $badFormatUrl $baseHeaders
Assert-Equal $resp.Status 400 "invalid date format returns 400"

$badVersionUrl = Build-Url $Url @{
  v = "999"
  date_from = "2024-01-01"
  date_to   = "2024-01-15"
}
$resp = Invoke-Http $badVersionUrl $baseHeaders
Assert-Equal $resp.Status 400 "unsupported API version returns 400"

if ($RateLimitTest) {
  $hitRateLimit = $false
  for ($i = 0; $i -lt $RateLimitRequests; $i++) {
    $resp = Invoke-Http $okUrl $baseHeaders
    if ($resp.Status -eq 429) {
      $hitRateLimit = $true
      break
    }
  }
  if ($hitRateLimit) {
    Write-Output "OK: rate limit triggered (429)"
  } else {
    Write-Warning "Rate limit not triggered. This is best-effort and may vary by instance."
  }
}

if ($script:failed) {
  Write-Error "Public stats tests failed."
  exit 1
}

Write-Output "All public stats tests passed."
