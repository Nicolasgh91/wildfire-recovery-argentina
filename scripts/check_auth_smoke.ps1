$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$Token,
  [string]$ApiKey,
  [switch]$SkipCheckout
)

$BaseUrl = $BaseUrl.TrimEnd("/")

if (-not $Token) {
  $Token = $env:TOKEN
}
if (-not $Token) {
  Write-Error "TOKEN is required. Set `$env:TOKEN or pass -Token."
  exit 1
}

if (-not $ApiKey) {
  $ApiKey = $env:API_KEY
}
if (-not $ApiKey -and (Test-Path ".env")) {
  $line = (Select-String -Path ".env" -Pattern "^API_KEY=" -ErrorAction SilentlyContinue).Line
  if ($line) {
    $ApiKey = $line.Split("=")[1].Trim().Trim('"')
  }
}

$headers = @{ Authorization = "Bearer $Token" }
if ($ApiKey) {
  $headers["x-api-key"] = $ApiKey
}

function Invoke-Api {
  param(
    [string]$Method,
    [string]$Url,
    [string]$Body,
    [int[]]$OkStatus
  )

  $params = @{
    Uri            = $Url
    Method         = $Method
    Headers        = $headers
    UseBasicParsing = $true
    ErrorAction    = "Stop"
  }
  if ($Body) {
    $params["Body"] = $Body
    $params["ContentType"] = "application/json"
  }

  $status = 0
  $content = ""

  try {
    $resp = Invoke-WebRequest @params
    $status = [int]$resp.StatusCode
    $content = $resp.Content
  } catch [System.Net.WebException] {
    $resp = $_.Exception.Response
    if ($resp) {
      $status = [int]$resp.StatusCode
      $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
      $content = $reader.ReadToEnd()
      $reader.Close()
    } else {
      throw
    }
  }

  Write-Host "$Method $Url -> $status"

  if ($status -eq 401) {
    Write-Error "Unauthorized (401) - check access token."
    exit 1
  }

  if ($OkStatus -and ($OkStatus -notcontains $status)) {
    Write-Warning "Unexpected status $status. Response: $content"
  }

  return @{
    Status  = $status
    Content = $content
  }
}

Write-Host "Auth smoke check | BaseUrl=$BaseUrl"

# Audit search
Invoke-Api "GET" "$BaseUrl/api/v1/audit/search?q=chubut&limit=20&radius_km=1" $null @(200) | Out-Null

# Fire events search (public) -> fire_event_id
$fire = Invoke-RestMethod -Uri "$BaseUrl/api/v1/fire-events/search?q=chubut&page_size=1" -Method GET
if (-not $fire.fires -or -not $fire.fires[0].id) {
  Write-Error "fire_event_id not found in fire-events/search response."
  exit 1
}
$fireId = $fire.fires[0].id

# Explorations create + list (requires trailing slash)
$body = @{ fire_event_id = $fireId; title = "Auth smoke" } | ConvertTo-Json
Invoke-Api "POST" "$BaseUrl/api/v1/explorations/" $body @(201, 200) | Out-Null
Invoke-Api "GET" "$BaseUrl/api/v1/explorations/" $null @(200) | Out-Null

# Payments
Invoke-Api "GET" "$BaseUrl/api/v1/payments/credits/balance" $null @(200) | Out-Null
if (-not $SkipCheckout) {
  $checkoutBody = @{ purpose = "credits"; credits_amount = 5; client_platform = "web" } | ConvertTo-Json
  Invoke-Api "POST" "$BaseUrl/api/v1/payments/checkout" $checkoutBody @(200, 400, 502) | Out-Null
}

Write-Host "Auth smoke check completed."
