"""Core classes for administering the mail server database.

Classes and functions for inspecting and manipulating the database associated with
a Postfix- and Dovecot-based mail server configured according to the instructions from
Linode (https://www.linode.com/docs/guides/email-with-postfix-dovecot-and-mysql/).
"""
import configparser
from copy import copy
import sys
from typing import Callable, Iterable

import pymysql

def first_or_default(sequence: Iterable, condition: Callable[[], bool], default=None):
    """Return the first item in the sequence matching the condition.

    Parameters
    ----------
    sequence : Iterable
        The sequence to search for an item to match the condition.
    condition : callable
        The condition to be met in the form of a callback function which accepts objects in
        the sequence and returns a boolean.
    default : Object
        What to return if no item in the sequence matches the condition.

    Returns
    -------
    Object
        The first object in the sequence to satisfy the condition.
    """
    return next((item for item in sequence if condition(item)), default)

def first_or_default_index(sequence: Iterable, condition: Callable[[], bool], default=-1):
    """Return the index of the first item in the sequence matching the condition.

    Parameters
    ----------
    sequence : Iterable
        The sequence to search for an item to match the condition.
    condition : callable
        The condition to be met in the form of a callback function which accepts objects in the
        sequence and returns a boolean.
    default : int
        What to return if no item in the sequence matches the condition (default -1)

    Returns
    -------
    int
        The index of the first item matching the condition.
    """
    for i, item in enumerate(sequence):
        if condition(item):
            return i
    return default


def _get_last_insert_id(db: pymysql.connections.Connection):
    """Return the most recently auto-incremented ID from the database.

    Parameters
    ----------
    db : pymysql.connections.Connection
        A connection to the database.

    Returns
    -------
    int
        The last auto-incremented ID.
    """

    with db.cursor() as cur:
        cur.execute('SELECT LAST_INSERT_ID()')
        db.commit()
        return int(cur.fetchone()[0])

class DatabaseException(Exception):
    """Custom exception to raise when user makes invalid database requests."""

class Domain:
    """A representation of an email domain database entry.

    Attributes
    ----------
    id : int
        The ID of the domain.
    name : str
        The name of the domain.
    """

    def __init__(self, domain_id, name, table_names):
        self.id = domain_id or 0
        self.name = name
        self.table_name = table_names['domains']

    def create(self, db):
        """Insert a new domain into the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        int or bool
            The ID of the newly-inserted item if successful. `False` otherwise.
        """
        with db.cursor() as cur:
            cur.execute(f'INSERT INTO {self.table_name} (name) VALUES ( %s )',
                        self.name)

            db.commit()

            if cur.rowcount > 0:
                new_id = _get_last_insert_id(db)
                self.id = new_id
                return new_id

            return False

    def update(self, db):
        """Update an existing domain in the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        bool
            Whether the update was successful.
        """
        with db.cursor() as cur:
            cur.execute(f'UPDATE {self.table_name} SET name=%s WHERE id=%s',
                            (self.name, self.id) )
            db.commit()

            return cur.rowcount > 0

    def delete(self, db):
        """Delete a domain from the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        bool
            Whether the delete was successful.
        """
        if self.id == 0:
            return False

        with db.cursor() as cur:
            cur.execute(f'DELETE FROM {self.table_name} WHERE id=%s', self.id)
            db.commit()

            return cur.rowcount > 0


class User:
    """A representation of an email user database entry.

    Attributes
    ----------
    id : int
        The ID of the user.
    domain_id : int
        The ID of the user's email domain.
    email : str
        The full email address of the user.
    password : str
        The user's password (only ever populated with user input for changing/creating).
    """

    def __init__(self, user_id: int, domain_id: int, email: str, table_names):
        self.id = int(user_id) or 0
        self.domain_id = int(domain_id)
        self.email = email
        self.password = ''
        self.table_name = table_names['users']


    def create(self, db):
        """Insert a new user into the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        int or bool
            The ID of the newly-inserted item if successful. `False` otherwise.
        """
        with db.cursor() as cur:
            cur.execute(f'INSERT INTO {self.table_name} (domain_id, password, email) VALUES ' +
                        "( %s, ENCRYPT(%s, CONCAT('$6$', SUBSTRING(SHA(RAND()), -16))), %s )",
                            (self.domain_id, self.password, self.email))

            db.commit()

            if cur.rowcount > 0:
                new_id = _get_last_insert_id(db)
                self.id = new_id
                return new_id
            return False

    def update(self, db):
        """Update an existing user in the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        bool
            Whether the update was successful.
        """
        with db.cursor() as cur:
            cur.execute(f'UPDATE {self.table_name} SET domain_id=%s, email=%s WHERE id=%s',
                            (self.domain_id, self.email, self.id))
            db.commit()
            if self.password:
                cur.execute((f"UPDATE {self.table_name} "
                             "SET password=ENCRYPT(%s, CONCAT('$6$', SUBSTRING(SHA(RAND()), -16))) "
                             "WHERE id=%s"),
                            (self.password, self.id))

            return cur.rowcount > 0

    def delete(self, db):
        """Delete an existing user from the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        bool
            Whether the delete was successful.
        """
        if self.id == 0:
            return False

        with db.cursor() as cur:
            cur.execute(f'DELETE FROM {self.table_name} WHERE id=%s', self.id)
            db.commit()

            return cur.rowcount > 0


class Alias:
    """A representation of an email alias database entry.

    Attributes
    ----------
    id : int
        The ID of the user.
    domain_id : int
        The ID of the user's email domain.
    source : str
        The full email address whose mail should be forwarded.
    destination : str
        The full email address which should receive forwarded mail.
    """

    def __init__(self, alias_id: int, domain_id: int, source: str, destination: str, table_names):
        self.id = int(alias_id) or 0
        self.domain_id = int(domain_id)
        self.source = source
        self.destination = destination
        self.table_name = table_names['aliases']


    def create(self, db):
        """Insert a new alias into the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        int or bool
            The ID of the newly-inserted item if successful. `False` otherwise.
        """
        with db.cursor() as cur:
            cur.execute(f'INSERT INTO {self.table_name} (domain_id, source, destination) ' +
                        'VALUES ( %s, %s, %s )',
                        (self.domain_id, self.source, self.destination))
            db.commit()

            if cur.rowcount > 0:
                new_id = _get_last_insert_id(db)
                self.id = new_id
                return new_id
            return False

    def update(self, db):
        """Update an existing alias in the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        bool
            Whether the update was successful.
        """
        with db.cursor() as cur:
            cur.execute(f'UPDATE {self.table_name} ' +
                        'SET domain_id=%s, source=%s, destination=%s WHERE id=%s',
                        (self.domain_id, self.source, self.destination, self.id))
            db.commit()

            return cur.rowcount > 0

    def delete(self, db):
        """Delete an existing alias from the database.

        Parameters
        ----------
        db : pymysql.connections.Connection
            A connection to the database.

        Returns
        -------
        bool
            Whether the delete was successful.
        """
        if self.id == 0:
            return False

        with db.cursor() as cur:
            cur.execute(f'DELETE FROM {self.table_name} WHERE id=%s', self.id)
            db.commit()

            return cur.rowcount == 1

class MailAdminDatabase:
    """A representation of the mailserver database.
    """

    def __init__(self):
        self._db = None

        config = configparser.ConfigParser()
        config.read('mailadmin.conf')

        try:
            host = config['connection']['host']
            user = config['connection']['user']
            dbname = config['connection']['dbname']
            password = config['connection']['password']

            self._table_names = {
                'domains': config['tables']['domains'],
                'users': config['tables']['users'],
                'aliases': config['tables']['aliases']
            }

            self._db = pymysql.connect(host, user, password, dbname)

        except KeyError as err:
            print('Configuration file "mailadmin.conf" not found or missing necessary elements:',
                   str(err))
            sys.exit(1)
        except pymysql.err.OperationalError as err:
            print('Database connection failed:')
            print(err)
            sys.exit(1)

        with self._db.cursor() as cur:
            cur.execute(f'SELECT * FROM {self._table_names["domains"]}')
            self._domains = [Domain(domain_id, name, self._table_names)
                             for domain_id, name in cur.fetchall()]

            cur.execute(f'SELECT id, domain_id, email FROM {self._table_names["users"]}')
            self._users = [User(user_id, domain_id, email, self._table_names)
                           for user_id, domain_id, email in cur.fetchall()]

            cur.execute(
                f'SELECT id, domain_id, source, destination FROM {self._table_names["aliases"]}')
            self._aliases = [Alias(alias_id, domain_id, source, destination, self._table_names)
                             for alias_id, domain_id, source, destination in cur.fetchall()]

    def print_domains(self):
        """Print a list of the known domains."""
        table = Table(('ID', 'Name'), ('>', '<'))
        for item in self._domains:
            table.add_row((item.id, item.name))
        table.print('    ')

    def get_domains(self):
        """Return lists of IDs and names of the domains.

        Returns
        -------
        ids : list of int
            The IDs of the domains.
        names : list of str
            The domain names.
        """
        return {
            'names': [d.name for d in self._domains],
            'ids': [d.id for d in self._domains]
        }

    def print_users(self):
        """Print a list of the known users."""
        table = Table(('ID', 'Domain ID', 'Email'), ('>', '>', '<'))
        for item in self._users:
            table.add_row((item.id, item.domain_id, item.email))
        table.print('    ')

    def get_users(self):
        """Return lists of IDs, domain IDs, and email addresses of the users.

        Returns
        -------
        ids : list of int
            The IDs of the users.
        domain_ids : list of int
            The IDs of the users' domains.
        emails : list of str
            The email addresses of the users.
        """
        return {
            'emails': [u.email for u in self._users],
            'ids': [u.id for u in self._users],
            'domain_ids': [u.domain_id for u in self._users]
        }

    def print_aliases(self):
        """Print a list of the aliases."""
        table = Table(('ID', 'Domain ID', 'Source', 'Destination'), ('>', '>', '<', '<'))
        for item in self._aliases:
            table.add_row((item.id, item.domain_id, item.source, item.destination))
        table.print('    ')

    def get_aliases(self):
        """Return lists of IDs, domain IDs, and source and destination addresses of the aliases.

        Returns
        -------
        ids : list of int
            The IDs of the users.
        domain_ids : list of int
            The IDs of the users' domains.
        sources : list of str
            The source email addresses of the users.
        destinations : list of str
            The destination email addresses of the users.
        """
        return {
            'sources': [a.source for a in self._aliases],
            'destinations': [a.destination for a in self._aliases],
            'ids': [a.id for a in self._aliases],
            'domain_ids': [a.domain_id for a in self._aliases]
        }

    def get_domain(self, domain_id: int = None):
        """Return a domain specified by an ID, or a new domain if no ID is given.

        Parameters
        ----------
        domain_id : int or None
            The ID of the domain to return, or `None` if a new domain is desired.

        Returns
        -------
        Domain
            The requested domain.

        Raises
        ------
        DatabaseException
            If an ID is given but the requested domain is not found.
        """
        if domain_id:
            result = first_or_default(self._domains, lambda d: d.id == domain_id)
            if result:
                return copy(result)
            raise DatabaseException('Domain not found.')
        return Domain(0, '', self._table_names)

    def get_domain_by_name(self, name: str) -> Domain:
        """Return a domain specified by a name.

        Parameters
        ----------
        name : str
            The name of the domain to return.

        Returns
        -------
        Domain
            The requested domain.

        Raises
        ------
        DatabaseException
            If the requested domain is not found.
        """
        domain = first_or_default(self._domains, lambda d: d.name == name)
        if domain:
            return domain
        raise DatabaseException('Domain not found.')

    def commit_domain(self, domain: Domain) -> Domain:
        """Insert or update a domain into or in the database.

        Parameters
        ----------
        domain : Domain
            The domain to be added or updated.

        Returns
        -------
        Domain
            The domain after being added or updated.

        Raises
        ------
        DatabaseException
            If the the invoker makes an invalid request.
        """
        # If the domain name already exists, it must be the same domain
        existing = first_or_default(self._domains, lambda d: d.name == domain.name)
        if existing is not None:
            # the domain name is already registered
            if existing.id == domain.id:
                # the domain is already present, so do nothing
                return domain
            raise DatabaseException("Domain already exists.")

        # the domain name is not already registered
        if domain.id == 0:
            # CREATE A NEW DOMAIN
            new_id = domain.create(self._db)
            if new_id:
                self._domains.append(domain)
                return domain
            raise DatabaseException("Domain creation failed.")

        # UPDATE THE DOMAIN
        success = domain.update(self._db)
        if success:
            index = first_or_default_index(self._domains, lambda d: d.id == domain.id)
            self._domains[index] = domain
            return domain
        raise DatabaseException("Domain update failed.")

    def delete_domain(self, domain_id: int) -> bool:
        """Delete the specified domain.

        Parameters
        ----------
        domain_id : int
            The ID of the domain to delete

        Returns
        -------
        bool
            Whether the deletion was successful.

        Raises
        ------
        DatabaseException
            If the user attempts to delete a domain which does not exist.
        """
        domain = first_or_default(self._domains, lambda d: d.id == domain_id)
        if not domain:
            raise DatabaseException('Domain does not exist.')
        success = domain.delete(self._db)
        if success:
            self._domains.remove(domain)
        return success

    def get_user(self, user_id: int = None) -> User:
        """Return a user specified by an ID, or a new user if no ID is given.

        Parameters
        ----------
        user_id : int or None
            The ID of the user to return, or `None` if a new user is desired.

        Returns
        -------
        User
            The requested user.

        Raises
        ------
        DatabaseException
            If an ID is given but the requested user is not found, or if there are no domains.
        """
        if user_id:
            result = first_or_default(self._users, lambda u: u.id == user_id)
            if result:
                return copy(result)
            raise DatabaseException('User not found.')

        if len(self._domains) == 0:
            raise DatabaseException('No domains registered. Cannot create a user.')
        return User(0, self._domains[0].id, f'name@{self._domains[0].name}', self._table_names)

    def get_user_by_email(self, email: str) -> User:
        """Return a user specified by an email address.

        Parameters
        ----------
        email : str
            The email address of the user to return.

        Returns
        -------
        User
            The requested user.

        Raises
        ------
        DatabaseException
            If no user is found with the given email address
        """
        user = first_or_default(self._users, lambda u: u.email == email)
        if user:
            return user
        raise DatabaseException('User not found.')

    def commit_user(self, user: User) -> User:
        """Update the database with a given user.

        Parameters
        ----------
        user : User
            The user to insert into or update in the database.

        Returns
        -------
        User
            The user after the insertion/update has completed.

        Raises
        ------
        DatabaseException
            If the user makes an invalid request.
        """
        requested_domain = first_or_default(self._domains, lambda d: d.id == user.domain_id)
        if not requested_domain:
            raise DatabaseException('Invalid domain.')

        existing = first_or_default(self._users, lambda u: u.email == user.email)
        if existing:
            if existing.id != user.id:
                raise DatabaseException('User already exists.')

        if not user.email.endswith(requested_domain.name):
            raise DatabaseException('Email must include the requested domain.')

        if user.password and len(user.password) < 8:
            raise DatabaseException('Password must be at least 8 characters.')

        if user.id == 0:
            new_id = user.create(self._db)
            if new_id:
                self._users.append(user)
                return user
            raise DatabaseException('User creation failed.')

        success = user.update(self._db)
        if success:
            index = first_or_default_index(self._users, lambda u: u.id == user.id)
            self._users[index] = user
            return user
        raise DatabaseException('User update failed.')

    def delete_user(self, user_id: int) -> bool:
        """Delete a user from the database.

        Parameters
        ----------
        user_id : int
            The ID of the user to delete.

        Returns
        -------
        bool
            Whether the deletion was successful.

        Raises
        ------
        DatabaseException
            If the user does not exist.
        """
        user = first_or_default(self._users, lambda u: u.id == user_id)
        if not user:
            raise DatabaseException('User does not exist.')
        success = user.delete(self._db)
        if success:
            self._users.remove(user)
        return success

    def delete_user_by_email(self, email: str) -> bool:
        """Delete a user, specified by an email address, from the database.

        Parameters
        ----------
        email : str
            The user's email address.

        Returns
        -------
        bool
            Whether the deletion was successful.

        Raises
        ------
        DatabaseException
            If the requested user does not exist.
        """
        user = first_or_default(self._users, lambda u: u.email == email)
        if not user:
            raise DatabaseException('User does not exist.')
        return self.delete_user(user.id)

    def get_alias(self, alias_id: int = None) -> Alias:
        """Return an alias specified by ID.

        Parameters
        ----------
        alias_id : int or None
            The ID of the alias to return, or `None` or 0 to create a new alias.

        Returns
        -------
        Alias
            The requested alias.

        Raises
        ------
        DatabaseException
            If the alias is not found, or if no valid combinations of domains and users are found
            to create an alias destination.
        """
        if alias_id:
            result = first_or_default(self._aliases, lambda a: a.id == alias_id)
            if result:
                return copy(result)
            raise DatabaseException("Alias not found.")
        dom = None
        for dom in self._domains:
            first_user = first_or_default(self._users,
                                          lambda u, domain=dom: u.domain_id == domain.id)
            if first_user:
                break
        if dom is None:
            return None
        if not first_user:
            raise DatabaseException("No valid user-domain combinations. Cannot create an alias.")

        return Alias(0, dom.id, f'name@{dom.name}', first_user.email, self._table_names)

    def commit_alias(self, alias: Alias) -> Alias:
        """Update the database with a given alias.

        Parameters
        ----------
        alias : Alias
            The alias to insert into or update in the database.

        Returns
        -------
        Alias
            The alias after the insertion/update has completed.

        Raises
        ------
        DatabaseException
            If the user makes an invalid request.
        """
        requested_domain = first_or_default(self._domains, lambda d: d.id == alias.domain_id)
        if not requested_domain:
            raise DatabaseException('Invalid domain.')
        existing = first_or_default(self._aliases,
                                    lambda a: a.source == alias.source
                                                and a.destination == alias.destination)
        if existing:
            if existing.id != alias.id:
                raise DatabaseException('Alias already exists.')
            if (existing.source == alias.source and existing.destination == alias.destination
                    and existing.domain_id == alias.domain_id):
                # Nothing to do
                return alias

        if alias.id == 0:
            new_id = alias.create(self._db)
            if new_id:
                self._aliases.append(alias)
                return alias
            raise DatabaseException('Alias creation failed.')

        success = alias.update(self._db)
        if success:
            return alias
        raise DatabaseException('Alias update failed.')

    def delete_alias(self, alias_id: int) -> bool:
        """Delete an alias from the database.

        Parameters
        ----------
        alias_id : int
            The ID of the alias to delete.

        Returns
        -------
        bool
            Whether the deletion was successful.

        Raises
        ------
        DatabaseException
            If the alias already did not exist.
        """
        alias = first_or_default(self._aliases, lambda a: a.id == alias_id)
        if not alias:
            raise DatabaseException('Alias does not exist.')
        success = alias.delete(self._db)
        if success:
            self._aliases.remove(alias)
        return success

    def __del__(self):
        if self._db:
            self._db.close()

class Table:
    """An object for printing nicely formatted tables"""

    def __init__(self, headings, alignments):
        """Create a new table

        Parameters
        ----------
        headings : list of str
            The headings for the table columns.
        alignments : list of str
            Alignment strings for the columns (each should be one of '<', '^', and '>' for left,
            center, or right, respectively).
        """
        self.rows = []
        self.headings = headings
        self.alignments = alignments
        self.col_lengths = [len(str(h)) for h in headings]

    def add_row(self, new_row):
        """Add a new row to the table.

        Parameters
        ----------
        new_row : list of str
            A list of new values to add to the table
        """
        self.rows.append(list(new_row))
        col_lengths = [len(str(col)) for col in new_row]
        if self.col_lengths is None:
            self.col_lengths = [0]*len(col_lengths)
        for i, col_length in enumerate(col_lengths):
            if col_length > self.col_lengths[i]:
                self.col_lengths[i] = col_length

    def print(self, sep='  '):
        """Print the contents of the table to the console.

        Parameters
        ----------
        sep : str
            The string to separate the columns of the table (Default: '  ').
        """
        fmt_string = sep.join([f'{{:{a}{l}}}' for a, l in zip(self.alignments, self.col_lengths)])
        print(fmt_string.format(*self.headings))
        for row in self.rows:
            print(fmt_string.format(*row))
