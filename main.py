import sys
import sqlite3
import datetime
import bcrypt
from PyQt5 import QtWidgets, QtCore

##########################
# Gestion de la base de données
##########################
class DatabaseManager:
    def __init__(self, db_file='bar_management.db'):
        # Connexion à la base SQLite (le fichier sera créé s'il n'existe pas)
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par leur nom
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Création de la table des boissons
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS drinks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL
            )
        ''')
        # Création de la table des transactions financières
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT
            )
        ''')
        # Création de la table des utilisateurs
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def add_user(self, username, password):
        # Hachage du mot de passe avec bcrypt
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def check_user(self, username, password):
        # Vérification du couple utilisateur/mot de passe
        self.cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        row = self.cursor.fetchone()
        if row:
            stored_hash = row['password']
            # Conversion éventuelle en bytes
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode('utf-8')
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
        return False

    def add_drink(self, name, quantity, price):
        self.cursor.execute('INSERT INTO drinks (name, quantity, price) VALUES (?, ?, ?)', (name, quantity, price))
        self.conn.commit()

    def update_drink(self, drink_id, quantity, price):
        self.cursor.execute('UPDATE drinks SET quantity = ?, price = ? WHERE id = ?', (quantity, price, drink_id))
        self.conn.commit()

    def delete_drink(self, drink_id):
        self.cursor.execute('DELETE FROM drinks WHERE id = ?', (drink_id,))
        self.conn.commit()

    def get_drinks(self):
        self.cursor.execute('SELECT * FROM drinks')
        return self.cursor.fetchall()

    def add_transaction(self, trans_type, amount, description):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('INSERT INTO transactions (date, type, amount, description) VALUES (?, ?, ?, ?)',
                            (date_str, trans_type, amount, description))
        self.conn.commit()

    def get_transactions(self):
        self.cursor.execute('SELECT * FROM transactions ORDER BY date DESC')
        return self.cursor.fetchall()

    def get_balance(self):
        self.cursor.execute('SELECT SUM(amount) as balance FROM transactions')
        row = self.cursor.fetchone()
        return row['balance'] if row['balance'] is not None else 0

    def close(self):
        self.conn.close()

##########################
# Fenêtre de Login
##########################
class LoginDialog(QtWidgets.QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("Login")
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        self.username_edit = QtWidgets.QLineEdit()
        self.username_edit.setPlaceholderText("Nom d'utilisateur")
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setPlaceholderText("Mot de passe")
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.Password)

        self.login_button = QtWidgets.QPushButton("Se connecter")
        self.login_button.clicked.connect(self.handle_login)

        layout.addWidget(self.username_edit)
        layout.addWidget(self.password_edit)
        layout.addWidget(self.login_button)
        self.setLayout(layout)

    def handle_login(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        if self.db_manager.check_user(username, password):
            self.accept()  # Connexion réussie
        else:
            QtWidgets.QMessageBox.warning(self, "Erreur", "Identifiants incorrects")

##########################
# Onglet de gestion des boissons
##########################
class DrinksTab(QtWidgets.QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setup_ui()
        self.load_drinks()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Tableau pour afficher les boissons
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nom", "Quantité", "Prix"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Formulaire d'ajout d'une boisson
        form_layout = QtWidgets.QHBoxLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("Nom de la boisson")
        self.quantity_edit = QtWidgets.QSpinBox()
        self.quantity_edit.setRange(0, 1000)
        self.price_edit = QtWidgets.QDoubleSpinBox()
        self.price_edit.setRange(0, 10000)
        self.price_edit.setDecimals(2)
        self.add_button = QtWidgets.QPushButton("Ajouter")
        self.add_button.clicked.connect(self.add_drink)

        form_layout.addWidget(self.name_edit)
        form_layout.addWidget(self.quantity_edit)
        form_layout.addWidget(self.price_edit)
        form_layout.addWidget(self.add_button)

        # Boutons pour modifier ou supprimer une boisson sélectionnée
        button_layout = QtWidgets.QHBoxLayout()
        self.update_button = QtWidgets.QPushButton("Modifier")
        self.update_button.clicked.connect(self.update_drink)
        self.delete_button = QtWidgets.QPushButton("Supprimer")
        self.delete_button.clicked.connect(self.delete_drink)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)

        layout.addWidget(self.table)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_drinks(self):
        drinks = self.db_manager.get_drinks()
        self.table.setRowCount(0)
        for row_data in drinks:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row_data["id"])))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(row_data["name"]))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(row_data["quantity"])))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(row_data["price"])))

    def add_drink(self):
        name = self.name_edit.text()
        quantity = self.quantity_edit.value()
        price = self.price_edit.value()
        if name:
            self.db_manager.add_drink(name, quantity, price)
            self.load_drinks()
            # Réinitialiser les champs
            self.name_edit.clear()
            self.quantity_edit.setValue(0)
            self.price_edit.setValue(0.0)
        else:
            QtWidgets.QMessageBox.warning(self, "Erreur", "Veuillez entrer un nom pour la boisson.")

    def update_drink(self):
        selected = self.table.selectedItems()
        if selected:
            drink_id = int(selected[0].text())
            # Utilisation des valeurs des spinbox pour la mise à jour
            quantity = self.quantity_edit.value()
            price = self.price_edit.value()
            self.db_manager.update_drink(drink_id, quantity, price)
            self.load_drinks()
        else:
            QtWidgets.QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une boisson à modifier.")

    def delete_drink(self):
        selected = self.table.selectedItems()
        if selected:
            drink_id = int(selected[0].text())
            self.db_manager.delete_drink(drink_id)
            self.load_drinks()
        else:
            QtWidgets.QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une boisson à supprimer.")

##########################
# Onglet de gestion des transactions
##########################
class TransactionsTab(QtWidgets.QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setup_ui()
        self.load_transactions()
        self.update_balance()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Tableau pour afficher les transactions
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Date", "Type", "Montant", "Description"])

        # Formulaire d'ajout d'une transaction
        form_layout = QtWidgets.QHBoxLayout()
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(["Achat", "Ajout"])
        self.amount_edit = QtWidgets.QDoubleSpinBox()
        self.amount_edit.setRange(0, 10000)
        self.amount_edit.setDecimals(2)
        self.description_edit = QtWidgets.QLineEdit()
        self.description_edit.setPlaceholderText("Description")
        self.add_button = QtWidgets.QPushButton("Ajouter Transaction")
        self.add_button.clicked.connect(self.add_transaction)

        form_layout.addWidget(self.type_combo)
        form_layout.addWidget(self.amount_edit)
        form_layout.addWidget(self.description_edit)
        form_layout.addWidget(self.add_button)

        # Affichage du solde
        self.balance_label = QtWidgets.QLabel("Solde: 0.00")

        layout.addWidget(self.table)
        layout.addLayout(form_layout)
        layout.addWidget(self.balance_label)
        self.setLayout(layout)

    def load_transactions(self):
        transactions = self.db_manager.get_transactions()
        self.table.setRowCount(0)
        for trans in transactions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(trans["id"])))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(trans["date"]))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(trans["type"]))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(trans["amount"])))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(trans["description"] if trans["description"] else ""))

    def update_balance(self):
        balance = self.db_manager.get_balance()
        self.balance_label.setText(f"Solde: {balance:.2f}")

    def add_transaction(self):
        trans_type = self.type_combo.currentText()
        amount = self.amount_edit.value()
        description = self.description_edit.text()
        # Pour un achat, le montant sera négatif (sortie d'argent)
        if trans_type == "Achat":
            amount = -abs(amount)
        else:
            amount = abs(amount)
        self.db_manager.add_transaction(trans_type, amount, description)
        self.load_transactions()
        self.update_balance()
        # Réinitialiser les champs
        self.amount_edit.setValue(0.0)
        self.description_edit.clear()

##########################
# Fenêtre principale avec onglets
##########################
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("Gestion du Bar de la Caserne")
        self.setup_ui()

    def setup_ui(self):
        self.tabs = QtWidgets.QTabWidget()
        self.drinks_tab = DrinksTab(self.db_manager)
        self.transactions_tab = TransactionsTab(self.db_manager)
        self.tabs.addTab(self.drinks_tab, "Boissons")
        self.tabs.addTab(self.transactions_tab, "Transactions")
        self.setCentralWidget(self.tabs)

        # Menu de base
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Fichier")
        exit_action = QtWidgets.QAction("Quitter", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

##########################
# Fonction principale
##########################
def main():
    app = QtWidgets.QApplication(sys.argv)
    db_manager = DatabaseManager()

    # Si aucun utilisateur n'existe, créer un compte admin par défaut (admin / admin)
    db_manager.cursor.execute("SELECT COUNT(*) as count FROM users")
    row = db_manager.cursor.fetchone()
    if row['count'] == 0:
        db_manager.add_user("admin", "admin")

    # Afficher la fenêtre de login
    login = LoginDialog(db_manager)
    if login.exec_() == QtWidgets.QDialog.Accepted:
        window = MainWindow(db_manager)
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit()

if __name__ == '__main__':
    main()
