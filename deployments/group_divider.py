import modal


image = (
    modal.Image.debian_slim()
    .run_commands("apt-get update && apt-get install curl -y")
    .run_commands("curl -fsSL https://pixi.sh/install.sh | sh")
    .add_local_dir("./app", "/usr/local/src/app", copy=True)
    .add_local_dir("./src", "/usr/local/src/src", copy=True)
    .add_local_file("./pyproject.toml", "/usr/local/src/pyproject.toml", copy=True)
    .add_local_file("./pixi.lock", "/usr/local/src/pixi.lock", copy=True)
    .add_local_file("./run.py", "/usr/local/src/run.py", copy=True)
    .workdir("/usr/local/src")
    .run_commands("/root/.pixi/bin/pixi install")
)

volume = modal.Volume.from_name("small-group-divider", create_if_missing=True)

app = modal.App(name="small-group-divider")


@app.function(
    image=image,
    volumes={"/usr/local/src/data": volume},
    secrets=[modal.Secret.from_name("small-group-divider")],
)
@modal.web_server(8139, startup_timeout=120)
def run_app():
    import subprocess

    subprocess.Popen("/root/.pixi/bin/pixi run python run.py", shell=True)
