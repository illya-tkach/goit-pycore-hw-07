from collections import UserDict
from datetime import date, datetime, timedelta

DATE_FORMAT = "%d.%m.%Y"
DAYS_AHEAD = 7


class Field:
    """Базовий клас для полів запису."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """Ім'я контакту (обов'язкове поле)."""

    def __init__(self, value):
        if not value or not value.strip():
            raise ValueError("Name is required.")
        super().__init__(value)


class Phone(Field):
    """Номер телефону: рівно 10 цифр."""

    def __init__(self, value):
        if not (isinstance(value, str) and value.isdigit() and len(value) == 10):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)


class Birthday(Field):
    """День народження у форматі DD.MM.YYYY (зберігається як datetime)."""

    def __init__(self, value):
        try:
            parsed = datetime.strptime(value, DATE_FORMAT)
        except (ValueError, TypeError):
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        if parsed.date() > date.today():
            raise ValueError("Birthday cannot be in the future.")
        super().__init__(parsed)

    def __str__(self):
        return self.value.strftime(DATE_FORMAT)


class Record:
    """Запис контакту: ім'я, телефони та необов'язковий день народження."""

    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None  # може бути лише один

    def add_phone(self, phone):
        self.phones.append(Phone(phone))

    def remove_phone(self, phone):
        found = self.find_phone(phone)
        if found is None:
            raise ValueError(f"Phone {phone} not found.")
        self.phones.remove(found)

    def edit_phone(self, old_phone, new_phone):
        found = self.find_phone(old_phone)
        if found is None:
            raise ValueError(f"Phone {old_phone} not found.")
        # Спершу створюємо новий Phone, щоб невалідний номер не зіпсував запис
        self.phones[self.phones.index(found)] = Phone(new_phone)

    def find_phone(self, phone):
        """Повертає об'єкт Phone або None, якщо номера немає."""
        return next((p for p in self.phones if p.value == phone), None)

    def add_birthday(self, birthday):
        """Додає (або замінює) день народження."""
        self.birthday = Birthday(birthday)

    def __str__(self):
        phones = "; ".join(p.value for p in self.phones)
        birthday = f", birthday: {self.birthday}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones}{birthday}"


def _birthday_in_year(birthday: date, year: int) -> date:
    """День народження в заданому році (29.02 -> 01.03 у невисокосні роки)."""
    try:
        return birthday.replace(year=year)
    except ValueError:
        return date(year, 3, 1)


class AddressBook(UserDict):
    """Адресна книга: ключ — ім'я, значення — Record."""

    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        """Повертає Record за ім'ям або None."""
        return self.data.get(name)

    def delete(self, name):
        if name not in self.data:
            raise KeyError(name)
        del self.data[name]

    def get_upcoming_birthdays(self, today=None):
        """Контакти, яких треба привітати протягом наступних 7 днів.

        Якщо день народження випадає на вихідний, привітання переноситься
        на понеділок. Повертає список {"name", "congratulation_date"}.
        """
        today = today or date.today()
        upcoming = []

        for record in self.data.values():
            if record.birthday is None:
                continue

            birthday = _birthday_in_year(record.birthday.value.date(), today.year)
            if birthday < today:
                birthday = _birthday_in_year(record.birthday.value.date(), today.year + 1)

            if (birthday - today).days > DAYS_AHEAD:
                continue

            congratulation_date = birthday
            if congratulation_date.weekday() >= 5:  # субота або неділя
                congratulation_date += timedelta(days=7 - congratulation_date.weekday())

            upcoming.append(
                {
                    "name": record.name.value,
                    "congratulation_date": congratulation_date,
                }
            )

        return sorted(upcoming, key=lambda item: item["congratulation_date"])


def input_error(func):
    """Декоратор: перетворює помилки введення на повідомлення для користувача."""

    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # Повідомлення задають самі моделі та обробники
            return str(e)
        except KeyError:
            return "Contact not found."
        except IndexError:
            return "Enter the argument for the command"

    return inner


def parse_input(user_input):
    """Повертає команду (нижній регістр) та її аргументи."""
    cmd, *args = user_input.split() or [""]
    return cmd.strip().lower(), *args


def _get_record(book, name):
    """Повертає запис або кидає KeyError, якщо контакту немає."""
    record = book.find(name)
    if record is None:
        raise KeyError(name)
    return record


@input_error
def add_contact(args, book: AddressBook):
    name, phone = args[0], args[1]  # IndexError, якщо бракує аргументів
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        message = "Contact added."
    record.add_phone(phone)  # валідація до додавання запису в книгу
    book.add_record(record)
    return message


@input_error
def change_contact(args, book: AddressBook):
    name, old_phone, new_phone = args[0], args[1], args[2]
    _get_record(book, name).edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error
def show_phone(args, book: AddressBook):
    record = _get_record(book, args[0])
    if not record.phones:
        return f"{record.name} has no phones."
    return "; ".join(p.value for p in record.phones)


@input_error
def show_all(args, book: AddressBook):
    if not book.data:
        return "No contacts saved."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args, book: AddressBook):
    name, birthday = args[0], args[1]
    _get_record(book, name).add_birthday(birthday)
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook):
    record = _get_record(book, args[0])
    if record.birthday is None:
        return f"{record.name} has no birthday set."
    return str(record.birthday)


@input_error
def birthdays(args, book: AddressBook):
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next week."
    return "\n".join(
        f"{item['name']}: {item['congratulation_date'].strftime(DATE_FORMAT)}"
        for item in upcoming
    )


def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        command, *args = parse_input(user_input)

        if command in ["close", "exit"]:
            print("Good bye!")
            break
        elif command == "hello":
            print("How can I help you?")
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_contact(args, book))
        elif command == "phone":
            print(show_phone(args, book))
        elif command == "all":
            print(show_all(args, book))
        elif command == "add-birthday":
            print(add_birthday(args, book))
        elif command == "show-birthday":
            print(show_birthday(args, book))
        elif command == "birthdays":
            print(birthdays(args, book))
        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
