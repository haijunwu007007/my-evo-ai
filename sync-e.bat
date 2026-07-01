@echo off
echo Syncing AUTO-EVO-AI to E drive...
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\frontend\*.html" "E:\AUTO-EVO-AI-V0.1\frontend\"
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\frontend\*.js" "E:\AUTO-EVO-AI-V0.1\frontend\"
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\frontend\*.css" "E:\AUTO-EVO-AI-V0.1\frontend\"
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\api\*.py" "E:\AUTO-EVO-AI-V0.1\api\"
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\modules\*.py" "E:\AUTO-EVO-AI-V0.1\modules\"
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\sdk\*" "E:\AUTO-EVO-AI-V0.1\sdk\"
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\install\*" "E:\AUTO-EVO-AI-V0.1\install\"
xcopy /E /Y /I /Q "D:\AUTO-EVO-AI-V0.1\tests\*" "E:\AUTO-EVO-AI-V0.1\tests\"
echo Sync complete!
