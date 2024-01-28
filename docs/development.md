# Setting up development environment

## Creating the Python development environment
First install all the prerequisites described in the README.md.

Acto requires Python version >=3.10.
If your system Python does not satisfy this requirement (Ubuntu20.04 depends on Python3.8),
  you would need to manually install another Python and create a venv for developing and using Acto.

To create a venv for Acto with the right Python installation,
run `python3.10 -m venv /path/to/new/virtual/environment`.
Then activate the venv by running `source .venv/bin/activate`.

While the virtual environment is active, `python3`/`python` commands would point to the Python in the virtual environment,
and `pip` would install packages inside the virtual environment.
To install the development requirements, run `python3 -m pip install -r requirements-dev.txt`.

## Coding style
We use several tools to help the development of Acto.
We use `black` to format the code to adhere to the pep8 style,
`isort` to clean the import statements,
`pylint` to lint the source code.
Optionally, we use `mypy` to do type checking.

Check out the [pyproject.toml](../pyproject.toml) for their configurations.

We follow [Google's Python Style Guide](https://google.github.io/styleguide/pyguide.html).

Acto current is going through the process of transitioning from research prototype to a mature
  open-source project, so you will find some part of the code not adhering the coding style.
We are updating the codebase progressively, and the coding style is only enforced on the changed files
 in the commit.

## Install the pre-commit hooks
Acto comes with pre-commit hooks to enforce some coding style.
They are run at the time you run `git commit ...`, and would report errors or format code.
To install the pre-commit hooks, run
```sh
pip install pre-commit
pre-commit install
```


# Schema Matching and Pruning for Testcase Generation
![Input Model Diagram](./input_model.jpg)
The diagram illustrates the sequence of operation applied to the `DeterministicInputModel` class from within the `Acto.__init__`, detailing the steps for automatic and manual CRD schema matching and pruning for generating test cases. Furthermore, it provides a visual representation of the class inheritance hierarchy for both schemas and value generator classes.
