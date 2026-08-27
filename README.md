# Password Generator

A secure password generator with a graphical interface and a built-in
Polish word list.

The application provides two password generation modes:

* **Password Manager** — highly random passwords suitable for password managers.
* **Human** — more readable passwords generated from randomly selected words.

## Features

* Password Manager mode
* Human-readable password mode
* Cryptographically secure random generation using Python `secrets`
* Built-in Polish word list
* Support for custom `.txt` word lists
* Configurable password length
* Configurable number of words
* Uppercase letters
* Lowercase letters
* Numbers
* Special characters
* Multiple separators
* Random separator selection
* Copy generated passwords to clipboard
* PySide6 graphical interface
* Input validation and error handling
* Automated test suite
* GitHub Actions CI

## Requirements

* Python 3.14+
* PySide6

For development and testing:

* pytest
* pytest-qt

## Installation

Clone the repository:

```bash
git clone git@github.com:Franek2009/Password-Generator.git
cd Password-Generator
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install the application dependencies:

```bash
python -m pip install -r requirements.txt
```

If you want to run the test suite or develop the project, install the
development dependencies instead:

```bash
python -m pip install -r requirements-dev.txt
```

## Running the Application

Start the application with:

```bash
python main.py
```

## Password Manager Mode

Password Manager mode generates highly random passwords using
cryptographically secure randomness provided by Python's `secrets` module.

The following character sets can be enabled independently:

* Uppercase letters
* Lowercase letters
* Numbers
* Special characters

The password length can be configured from **8 to 64 characters** through
the graphical interface.

At least one character set must be enabled.

When multiple character sets are selected, the generator guarantees that
at least one character from every selected set is present in the password,
provided that the requested length is sufficient.

## Human Mode

Human mode generates more readable passwords from randomly selected words.

The user can configure:

* Number of words
* Separator
* Word list
* Numbers
* Special characters

Supported separators:

```text
-
_
.
(space)
/
|
Random
```

When `Random` is selected, one separator is chosen randomly and used
consistently throughout the generated password.

### Word Selection

Words are selected without replacement when the word list contains enough
entries.

If more words are requested than are available in the word list, the
remaining words are selected with replacement.

Words are capitalized before being combined into the password.

Numbers and special characters can be added as separate password parts.

### Example

```text
Rower-Zamek-Las-Kawa42!
```

The exact output is random and will be different each time.

## Custom Word Lists

Human mode supports custom word lists stored as `.txt` files.

A word list should contain one word per line.

Example:

```text
kot
pies
zamek
rower
las
```

Custom word lists are validated before being used.

The application handles errors such as:

* missing word lists
* empty word lists
* invalid word list data

## Architecture

The application separates configuration, password generation,
word-list handling and the graphical interface.

The general flow is:

```text
User
  ↓
PySide6 GUI
  ↓
PasswordConfig
  ↓
Configuration validation
  ↓
Password generator
  ├── Password Manager mode
  │      ↓
  │   Character sets
  │      ↓
  │   Secure random generation
  │
  └── Human mode
         ↓
      Word list
         ↓
      Secure random word selection
  ↓
Generated password
  ↓
GUI / Clipboard
```

## Project Structure

```text
Password-Generator/
├── app/
│   ├── config.py
│   ├── generator.py
│   ├── ui.py
│   └── wordlist.py
├── data/
│   ├── words.txt
│   └── README.md
├── tests/
│   ├── test_generator.py
│   ├── test_ui.py
│   └── test_wordlist.py
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
└── README.md
```

### `main.py`

Application entry point.

Starts the PySide6 graphical interface.

### `app/config.py`

Defines the password configuration and validation logic.

Main components:

* `PasswordMode`
* `PasswordConfig`

The configuration validates settings before password generation.

### `app/generator.py`

Contains the password generation logic.

Main functionality:

* Human password generation
* Password Manager generation
* Mode selection
* Secure random selection
* Random separator selection
* Character-set handling
* Word selection without replacement when possible

Python's `secrets` module is used for security-sensitive randomness.

### `app/wordlist.py`

Handles loading and validating word lists.

It provides access to the built-in Polish word list as well as custom
word-list files.

### `app/ui.py`

Contains the PySide6 graphical interface.

The interface is responsible for:

* selecting the password mode
* configuring generation settings
* selecting custom word lists
* displaying generated passwords
* copying passwords to the clipboard
* displaying configuration and word-list errors

### `tests/test_generator.py`

Tests password generation and configuration validation.

The tests cover both Password Manager and Human modes, including
edge cases and custom word lists.

### `tests/test_ui.py`

Tests the PySide6 graphical interface.

The tests cover:

* mode switching
* sliders
* character-set controls
* separators
* word lists
* password generation
* clipboard functionality
* error handling

### `tests/test_wordlist.py`

Tests word-list loading and validation.

## Testing

The project uses `pytest` and `pytest-qt`.

Install the development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the complete test suite:

```bash
python -m pytest
```

The current test suite contains **85 tests** covering:

* password generation
* configuration validation
* Human mode
* Password Manager mode
* character-set handling
* password length edge cases
* word selection
* custom word lists
* invalid and missing word lists
* GUI behaviour
* mode switching
* clipboard functionality
* error handling

A successful run should look similar to:

```text
85 passed
```

## Code Quality Checks

Before committing changes, the project can be checked with:

```bash
python -m pytest
git diff --check
git status
```

GitHub Actions also runs the automated test suite.

## Security

Password generation uses Python's `secrets` module rather than the
standard `random` module.

This is important because `secrets` is designed for generating values
that need to be unpredictable, such as passwords and other security
tokens.

The Password Manager mode also guarantees that each selected character
set is represented in the generated password when the configured length
allows it.

Generated passwords are not intentionally persisted by the application.

## Built-in Word List

The built-in Polish word list is stored locally in:

```text
data/words.txt
```

The word list is based on the
[diceware-pl](https://github.com/MaciekTalaska/diceware-pl)
project by Maciek Tałaska.

The included word list is used under the MIT License.

See [`data/README.md`](data/README.md) for attribution and source
information.

## License

The Password Generator source code is licensed under the MIT License.

See [`LICENSE`](LICENSE) for the full license text.

## Status

The project is functional and tested.

The current version provides:

* secure password generation
* Password Manager mode
* Human mode
* custom word lists
* configurable generation options
* PySide6 graphical interface
* clipboard support
* validation and error handling
* automated tests
* continuous integration

The project is considered complete in its current scope.

## Credits

The built-in Polish word list is based on
[diceware-pl](https://github.com/MaciekTalaska/diceware-pl)
by Maciek Tałaska.

If you use this project, attribution is appreciated.
