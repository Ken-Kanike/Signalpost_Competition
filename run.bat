@echo off
rem ==============================================================================
rem Signalpost: Autonomous Norwegian Corporate Intelligence Agent
rem Windows One-Command Execution Wrapper
rem Usage: run.bat [target] [output_dir]
rem ==============================================================================

set TARGET=%~1
if "%TARGET%"=="" set TARGET=923609016

set OUTPUT_DIR=%~2
if "%OUTPUT_DIR%"=="" set OUTPUT_DIR=output

echo ==========================================================
echo  Signalpost Norwegian Company Research Agent
echo  Target:     %TARGET%
echo  Output Dir: %OUTPUT_DIR%
echo ==========================================================

python main.py run "%TARGET%" --output-dir "%OUTPUT_DIR%"
