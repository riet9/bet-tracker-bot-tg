import subprocess

def git_backup_push():
    subprocess.run(["git", "add", "backups/users_data.json"])
    subprocess.run(["git", "commit", "-m", "Auto backup"])
    subprocess.run(["git", "push"])

if __name__ == "__main__":
    git_backup_push()
