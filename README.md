# a10y

The current repository hosts a user interface terminal application for the Availability webservice.

The application is mainly built using [textual](https://textual.textualize.io/) library for making terminal applications.

## Demo video

[![asciicast](https://asciinema.org/a/HybCoSNhMJbNm2Ff8NH6zomTS.svg)](https://asciinema.org/a/HybCoSNhMJbNm2Ff8NH6zomTS)

# Installation

### Using `uv` from PyPI
If uv is not already installed, you can follow those [instructions](https://docs.astral.sh/uv/getting-started/installation/).

## Install EIDA a10y using uv
```bash
uvx eida-a10y
```
## Run the application
```bash
eida-a10y
```

### Using uv from the sources

Then follow those commands:

    git clone https://github.com/EIDA/a10y.git
    cd a10y
    uv sync
    uv run src/main.py

### Docker container

    git clone https://github.com/EIDA/a10y.git
    cd a10y
    buildah bud -t a10y
    podman run -it a10y
    
### In a python virtual environment

Clone the sources, create a virtual environment, install dependencies and run as a python script:

```
git clone https://github.com/EIDA/a10y.git
cd a10y
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python a10y.py
```

### With conda

Supposing you have [anaconda](https://www.anaconda.com/) or [miniconda](https://docs.conda.io/projects/miniconda/en/latest/) installed in your system, follow the steps below.

Clone the sources, create a conda environment, install dependencies and run as a python script:

```
git clone https://github.com/EIDA/a10y.git
cd a10y
conda create --name a10yEnv python=3.8
conda activate a10yEnv
python -m pip install -r requirements.txt
python a10y.py
```

### With pyinstaller

This method is intended to provide a portable standalone executable for the application.

The executable can be created on every system using [pyinstaller](https://pyinstaller.org/en/stable/).

It has been tested in an Ubuntu machine with pyinstaller version 6.3.0.

**After having created a python or conda environment, activated it and installed dependencies as shown above**, install pyinstaller and execute it as below:

```
python -m pip install pyinstaller
pyinstaller --onefile --add-data "a10y.css:." a10y.py
```

This will create:

- an `a10y.spec` file
- a `build` folder
- a `dist` folder

Into `dist` folder you can find the final executable. By executing through terminal, as every other executable in your system, it opens the application:

```
cd dist
./a10y
```

The final executable can be redistributed and be used as a standalone executable to any system with similar operating system as the one in which it was created.

## Options

The application can be executed with the following options:

- `-p or --post` followed by path that points to a file to start the application using that file for making POST requests to availability webservice
- `-c or --config` followed by path that points to a configuration file to start the application using specific default values for requests

## Configuration

A `config.toml` file with some default values for the parameters of the requests can be provided, so that the application starts with them as selected.

With the configuration file, you can set your default values for starttime, endtime, quality, mergegaps or merge policy.

The application looks for the configuration file in this order:

- with the `-c` or `--config` command line option
- in the `$XDG_CONFIG_DIR/a10y` directory
- in the directory of the application script

## Customizing the layout

All the layout colors are described in a CSS file `a10y.css` that can be customized. This is not possible at the moment with the binary release, which embeds the CSS file.
