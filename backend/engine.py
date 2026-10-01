import subprocess, os, sys

def run_migrations():
    base_dir = os.path.dirname(__file__)
    alembic_ini = os.path.join(base_dir, "alembic.ini")
    my_env = os.environ.copy()
    subprocess.run([sys.executable, "-m", "alembic", "-c", alembic_ini, "upgrade", "head"], check=True, env=my_env)
