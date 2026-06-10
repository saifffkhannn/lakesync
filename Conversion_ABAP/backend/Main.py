import sys
from convert_folder import run_conversion

def main():
    print("Starting ABAP to Snowflake conversion...")
    
    # These match the exact arguments from your PowerShell command
    result = run_conversion(
        input_folder_path=r"D:\Accelerator\ABAP Conversion\backend\sample_abap",
        output_folder_path=r"D:\Accelerator\ABAP Conversion\backend\output\ai_converted",
        upload_snowflake=True,
        require_ai_success=True,
        recursive=True
    )
    
    if result == 0:
        print("Conversion finished successfully!")
    else:
        print("Conversion finished with errors.")
        sys.exit(result)

if __name__ == "__main__":
    main()
