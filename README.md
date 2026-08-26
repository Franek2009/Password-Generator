````markdown
# Password Generator

Secure password generator with Polish word list.

## Features

- Password Manager mode
- Human-readable password mode
- Cryptographically secure random generation using Python's `secrets`
- Polish word list based on Diceware
- Adjustable password length
- Uppercase, lowercase, numbers and special characters
- Copy generated passwords to clipboard
- PySide6 graphical interface

## Requirements

- Python 3.14+
- PySide6

## Installation

Clone the repository:

```bash
git clone git@github.com:Franek2009/Password-Generator.git
cd Password-Generator
````

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Usage

Run the application with:

```bash
python main.py
```

## Testing

Run the test suite with:

```bash
python -m pytest
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
│   └── words.txt
├── tests/
│   └── test_generator.py
├── main.py
├── requirements.txt
└── README.md
```

## Word List

The built-in Polish word list is based on the
[diceware-pl](https://github.com/MaciekTalaska/diceware-pl)
project.

The list contains 3888 words.

## License

See `LICENSE`.

````
