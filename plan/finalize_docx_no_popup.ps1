$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Join-Path $root '毕业设计论文_唐星星.docx'
$target = Join-Path $root '毕业设计论文_唐星星_最终版.docx'

if (Test-Path $target) {
    Remove-Item $target -Force
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $word.Options.UpdateLinksAtOpen = $false
    $doc = $word.Documents.Open($source, $false, $false, $false)
    $doc.UpdateStylesOnOpen = $false

    # 先更新目录和页码,再把所有域转换为普通文本,避免打开文档时询问是否更新域。
    foreach ($story in $doc.StoryRanges) {
        $range = $story
        while ($null -ne $range) {
            if ($range.Fields.Count -gt 0) {
                $range.Fields.Update() | Out-Null
            }
            $range = $range.NextStoryRange
        }
    }

    foreach ($story in $doc.StoryRanges) {
        $range = $story
        while ($null -ne $range) {
            while ($range.Fields.Count -gt 0) {
                $range.Fields.Item(1).Unlink()
            }
            $range = $range.NextStoryRange
        }
    }

    # 12 = wdFormatXMLDocument (.docx)
    $doc.SaveAs2($target, 12)
    $doc.Close(0)
    $doc = $null
}
finally {
    if ($null -ne $doc) {
        $doc.Close(0)
    }
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}

Write-Output "已另存为: $target"
