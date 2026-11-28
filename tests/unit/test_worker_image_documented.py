"""The packages the Dockerfile installs are the ones the worker image page says it installs."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
PAGE = (ROOT / "docs" / "WORKER_IMAGE.md").read_text(encoding="utf-8")
CI_TOOLCHAIN = {
    "latexmk",
    "texlive-luatex",
    "texlive-latex-recommended",
    "texlive-latex-extra",
    "texlive-pictures",
    "texlive-fonts-recommended",
    "tex-gyre",
    "texlive-plain-generic",
    "texlive-extra-utils",
    "epubcheck",
    "default-jre-headless",
    "poppler-utils",
}


def stage(name: str) -> str:
    """The text of one stage of the Dockerfile: the runtime stage is the last, unnamed one."""
    stages = re.split(r"^FROM [^\n]+$", DOCKERFILE, flags=re.MULTILINE)
    headers = re.findall(r"^FROM ([^\n]+)$", DOCKERFILE, flags=re.MULTILINE)
    for header, body in zip(headers, stages[1:], strict=True):
        if (" AS " not in header and name == "runtime") or header.endswith(f" AS {name}"):
            return body
    raise AssertionError(f"no {name} stage in the Dockerfile")


def apt_packages(body: str) -> set[str]:
    """The packages of the apt-get install command in a stage, which runs until the next ``&&`` that is not a package."""
    start = body.index("apt-get install")
    command = body[start:]
    command = command.split("rm -rf", 1)[0]
    words = command.replace("\\", " ").split()
    return {
        word
        for word in words
        if re.fullmatch(r"[a-z][a-z0-9.+-]*", word)
        and word not in {"apt-get", "install", "y", "no-install-recommends", "rm"}
    }


def test_the_runtime_image_installs_procps_which_provides_the_ps_the_meter_needs() -> None:
    assert apt_packages(stage("runtime")) == {"procps"}
    assert "`procps`" in PAGE


def test_the_tex_image_is_the_ci_toolchain_plus_the_packages_the_page_names() -> None:
    tex = apt_packages(stage("worker-tex"))

    assert CI_TOOLCHAIN <= tex
    assert tex - CI_TOOLCHAIN == {"zip", "tidy"}
    for name in sorted(tex - CI_TOOLCHAIN):
        assert f"`{name}`" in PAGE, f"WORKER_IMAGE.md does not name {name}"


def test_the_ci_toolchain_job_installs_the_same_packages_the_page_describes() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["toolchain"]["steps"]
    install = next(step for step in steps if step.get("name") == "Install the TeX toolchain")

    assert set(install["env"]["PACKAGES"].split()) == CI_TOOLCHAIN
