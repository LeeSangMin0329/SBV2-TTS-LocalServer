chcp 65001 > NUL
@echo off

pushd %~dp0
echo Running test_client_out_api.py...
venv\Scripts\python test_client_out_api.py

if %errorlevel% neq 0 ( pause & popd & exit /b %errorlevel% )

popd
pause
