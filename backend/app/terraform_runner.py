import subprocess
import os

def run_terraform_command(command: list) -> dict:
    """Helper to run terraform commands locally"""
    try:
        result = subprocess.run(
            ["terraform"] + command,
            capture_output=True,
            text=True,
            check=True
        )
        return {"success": True, "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr}

def deploy_terraform() -> dict:
    """Executes terraform init and apply."""
    # 1. Init
    init_res = run_terraform_command(["init"])
    if not init_res["success"]:
        return {"status": "error", "message": "Terraform Init Failed", "details": init_res["error"]}
    
    # 2. Apply
    apply_res = run_terraform_command(["apply", "-auto-approve"])
    if not apply_res["success"]:
        return {"status": "error", "message": "Terraform Apply Failed", "details": apply_res["error"]}
        
    return {"status": "success", "message": "Infrastructure deployed successfully!", "details": apply_res["output"]}

def destroy_terraform() -> dict:
    """Executes terraform destroy."""
    destroy_res = run_terraform_command(["destroy", "-auto-approve"])
    if not destroy_res["success"]:
         return {"status": "error", "message": "Terraform Destroy Failed", "details": destroy_res["error"]}
    return {"status": "success", "message": "Infrastructure destroyed.", "details": destroy_res["output"]}

def rollback_terraform() -> dict:
    """Uses terraform state to rollback by applying the previous state (simulated via state file check)."""
    # In a real world, we would use terraform state push or similar, but here we'll just check if a backup exists
    if os.path.exists("terraform.tfstate.backup"):
        # This is a simplification; terraform doesn't have a direct 'rollback' command, 
        # so we usually just re-apply a previous version of the code.
        # Here we just re-run apply to ensure the state matches the code.
        return run_terraform_command(["apply", "-auto-approve"])
    return {"success": False, "error": "No backup state found to rollback to."}
