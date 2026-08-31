# Start HareKrishnaAI Bot in background
$BotDir = "C:\Users\Test\Desktop\HareKrishnaAI"
Set-Location $BotDir

# Run bot in new hidden window
$process = Start-Process python -ArgumentList "-m app.bot" -WindowStyle Hidden -PassThru

Write-Host "Bot started with PID: $($process.Id)"
