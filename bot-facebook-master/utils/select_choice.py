import os

from utils.commands.hardware import get_hardware_id, verify_code

def select():
    print("Select an option:")
    print("1. Search and Comment")
    print("2. Comment in Group")
    print("3. Comment in Group Advance")
    print("4. Comment on Post")
    print("5. Post in Group")
    
    choice = input("Please select an option (1-5): ")
    
    if choice == '1':
        print("You selected: Search and Comment")
        choice_yes_or_no = yes_or_no()
        return f"{choice}.{choice_yes_or_no}"
    elif choice == '2':
        print("You selected: Comment in Group")
        choice_yes_or_no = yes_or_no()
        return f"{choice}.{choice_yes_or_no}"
    elif choice == '3':
        print("You selected: Comment in Group Advance")
        return choice
    elif choice == '4':
        print("You selected: Comment on Post")
        return choice
    elif choice == '5':
        print("You selected: Post in Group")
        return choice
    else:
        print("Invalid option, please try again.")
        return select()

def yes_or_no():
    print("Do you want to select the latest post?")
    print("1. Yes")
    print("2. No")
    
    choice_yes_or_no = input("Please select an option (1-2): ")
    if choice_yes_or_no == '1':
        print("You selected the latest post.")
        return choice_yes_or_no
    elif choice_yes_or_no == '2':
        print("You did not select the latest post.")
        return choice_yes_or_no
    else:
        print("Invalid option, please try again.")
        return yes_or_no()

def select_time():
    while True:
        try:
            time_input = int(input("Enter the repeat time in minutes (Enter 0 to disable repetition): "))
            return time_input
        except ValueError:
            print("Please enter a valid number!")

def select_auto():
    print("Do you want to simulate activity while waiting?")
    print("1. Yes")
    print("2. No")
    
    choice = input("Please select an option (1-2): ")
    
    if choice == '1':
        print("You selected: Simulate activity while waiting.")
        return True
    elif choice == '2':
        print("You selected: Do not simulate activity while waiting.")
        return False
    else:
        print("Invalid option, please try again.")
        return select_auto()

def check_code_file():
    hardware_id = get_hardware_id()
    file_path = "code.text"
    
    if os.path.isfile(file_path):
        with open(file_path, "r") as file:
            saved_code = file.read().strip()
        if verify_code(hardware_id, saved_code):
            print("Code in file is valid.")
            return True
    
    while True:
        code = input("Please enter the code: ")
        if verify_code(hardware_id, code):
            with open(file_path, "w") as file:
                file.write(code)
            print("Code has been saved to code.text.")
            return True
        else:
            print(f"Hardware ID: {hardware_id}")
            print("Invalid code, please try again.")
