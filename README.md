# Password Generator

A secure password generator with a graphical interface and a built-in
Polish word list.

The project provides two password generation modes: highly random
passwords for password managers and more human-readable passwords
based on randomly selected words.

## Features

- Password Manager mode
- Human-readable password mode
- Cryptographically secure random generation using Python `secrets`
- Built-in Polish word list
- Support for custom `.txt` word lists
- Configurable password length
- Configurable number of words
- Uppercase and lowercase letters
- Numbers
- Special characters
- Multiple separators
- Random separator selection
- Copy generated passwords to clipboard
- PySide6 graphical interface
- Automated test suite

## Requirements

- Python 3.14+
- PySide6

For development and testing:

- pytest

## Installation

Clone the repository:

```bash
git clone git@github.com:Franek2009/Password-Generator.git
cd Password-Generator
````

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

## Usage

Start the application with:

```bash
python main.py
```

### Password Manager mode

Generates random passwords using configurable character sets:

* uppercase letters
* lowercase letters
* numbers
* special characters

The password length can be adjusted from 8 to 64 characters.

### Human mode

Generates passwords using randomly selected words from a word list.

Example:

```text
Rower-Zamek-Las-Kawa42!
```

The number of words, separator and word list can be configured.

Custom word lists can be loaded from `.txt` files.

## Testing

Run the test suite with:

```bash
python -m pytest
```

The project contains tests covering password generation,
word list loading and error handling.

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
│   └── test_wordlist.py
├── main.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Word List

The built-in Polish word list contains 3888 words.

It is based on the
[diceware-pl](https://github.com/MaciekTalaska/diceware-pl)
project by Maciek Tałaska.

The included word list is used under the MIT License.
See `data/README.md` for attribution and source information.

## License

The Password Generator source code is licensed under the MIT License.

See [`LICENSE`](LICENSE) for the full license text.

## Status

The project is currently under development.

More features, improvements and security-related checks are planned.

## Credits

The built-in Polish word list is based on
[diceware-pl](https://github.com/MaciekTalaska/diceware-pl)
by Maciek Tałaska.

If you use this project, attribution is appreciated.
