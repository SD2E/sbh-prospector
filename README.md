# sbh-explorer
Allow exploration of a SynBioHub database

## Installation

SynBioHub explorer requires Python 3. You can install sbh-explorer
using [pip](https://docs.python.org/3/installing/index.html).

Here is an example installation within a
[virtual environment](https://docs.python.org/3/library/venv.html),
which can be a convenient way to install package without requiring
root access.

```shell
# Create a virtual environment named 'myenv'
python3 -m venv myenv

# Activate the virtual environment
source myenv/bin/activate

# Upgrade to the latest pip. sbh-explorer requires at least pip 18.1
python3 -m pip install --upgrade pip

# Install sbh-explorer. Dependencies will automatically install.
pip install --upgrade git+https://github.com/SD2E/sbh-explorer
```

## Example programs

See the [examples](examples) directory for sample programs.
