# Point qa.oscarmackjr.com -> QA ALB via Route 53 ALIAS record
# Run from anywhere with AWS CLI configured for account 014148916722

$HostedZoneId  = "Z0373747OZV6XKZZZEVK"  # oscarmackjr.com hosted zone
$AlbDnsName    = "intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com"
$AlbHostedZone = "Z35SXDOTRQ7X7K"         # AWS constant for ALBs in us-east-1
$RecordName    = "qa.oscarmackjr.com"

# Write JSON to a temp file — avoids PowerShell quoting issues with AWS CLI
$tmpFile = [System.IO.Path]::GetTempFileName()
@"
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$RecordName",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$AlbHostedZone",
          "DNSName": "$AlbDnsName",
          "EvaluateTargetHealth": true
        }
      }
    }
  ]
}
"@ | Out-File -Encoding ascii -FilePath $tmpFile

Write-Host "Creating ALIAS record: $RecordName -> $AlbDnsName"

$result = aws route53 change-resource-record-sets `
    --hosted-zone-id $HostedZoneId `
    --change-batch "file://$tmpFile" `
    --output json | ConvertFrom-Json

Remove-Item $tmpFile -ErrorAction SilentlyContinue

if ($LASTEXITCODE -ne 0) {
    Write-Error "Route 53 update failed."
    exit 1
}

$changeId = $result.ChangeInfo.Id
Write-Host "Change submitted: $changeId"
Write-Host "Status: $($result.ChangeInfo.Status)  (PENDING -> INSYNC usually within 1-2 min)"
Write-Host ""
Write-Host "Poll until INSYNC:"
Write-Host "  aws route53 get-change --id $changeId --query ChangeInfo.Status --output text"
Write-Host ""
Write-Host "Then test:"
Write-Host "  curl -I https://$RecordName"
