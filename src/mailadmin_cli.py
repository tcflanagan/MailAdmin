"""Command-line interface for administering the mail server database.

A simple command-line interface for inspecting and manipulating the database associated
with a Postfix- and Dovecot-based mail server configured according to the instructions
from Linode (https://www.linode.com/docs/guides/email-with-postfix-dovecot-and-mysql/).
"""

import argparse
from getpass import getpass

from src import mailadmin_core as core


def create_parser() -> argparse.ArgumentParser:
    """Run the command-line program."""
    parser = argparse.ArgumentParser(prog="MailAdmin",
                                     description=("Manage the users of a Dovcot/Postfix mail "
                                                 "server set up according to instructions at "
                                                 "linode.com."))

    subparsers = parser.add_subparsers(dest='area',
        help='Which type of entity you want to inspect or modify.',)


    parser_domains = subparsers.add_parser('domains',
                                        help='Inspect, add, or modify domains.')
    subparsers_domains = parser_domains.add_subparsers(help="What you want to do.", dest='command')
    #parser_domains_list = subparsers_domains.add_parser('list', help='List registered domains.')
    subparsers_domains.add_parser('list', help='List registered domains.')
    parser_domains_add = subparsers_domains.add_parser('add', help='Register a new domain.')
    parser_domains_add.add_argument('name', action='store',
                                    help='The hostname of the domain to add.')
    parser_domains_remove = subparsers_domains.add_parser('remove', help='Unregister a domain.')
    parser_domains_remove.add_argument('-n', '--by-name', action='store_true',
                                    help='Search by name, rather than by ID.')
    parser_domains_remove.add_argument('key', action='store',
                                    help='The ID (or name if -n is given) of the domain to remove.')
    parser_domains_edit = subparsers_domains.add_parser('edit', help='Edit a domain')
    parser_domains_edit.add_argument('-n', '--by-name', action='store_true',
                                    help='Search by name, rather than by ID.')
    parser_domains_edit.add_argument('key', action='store',
                                    help='The ID (or name if -n is given) of the domain to edit.')
    parser_domains_edit.add_argument('new-name', action='store', help='The new name of the domain.')

    parser_users = subparsers.add_parser('users',
                                        help='Inspect, add, or modify users.')
    subparsers_users = parser_users.add_subparsers(help="What you want to do.", dest="command")
    # parser_users_list = subparsers_users.add_parser('list', help='List registered users.')
    subparsers_users.add_parser('list', help='List registered users.')
    parser_users_add = subparsers_users.add_parser('add', help='Add a new user.')
    parser_users_add.add_argument('domain_id', action='store',
                                help='The ID of the domain to which the user will be added.')
    parser_users_add.add_argument('email', action='store',
                                  help='The email address of the new user.')
    parser_users_remove = subparsers_users.add_parser('remove', help='Remove a registered user.')
    parser_users_remove.add_argument('-e', '--by-email', action='store_true',
                                    help='Remove by email, rather than by ID.')
    parser_users_remove.add_argument('key', action="store",
                                    help='The ID (or email if -e is given) of the user to remove.')
    parser_users_edit = subparsers_users.add_parser('edit', help='Modify a registered user.')
    parser_users_edit.add_argument('-e', '--by-email', action='store_true',
                                help='Select by email, rather than by ID.')
    parser_users_edit.add_argument('key', action='store',
                                help='The ID (or email if -e is given) of the user to edit.')
    parser_users_edit.add_argument('-d', '--domain-id', action='store',
                                help='The new domain ID for the user.')
    parser_users_edit.add_argument('-n', '--new-email', action='store',
                                help='The new email address for the user.')
    parser_users_edit.add_argument('-p', '--change-password', action='store_true',
                                help='Change the password for the user.')

    parser_aliases = subparsers.add_parser('aliases',
                                        help='Inspect, add, or modify aliases.')
    subparsers_aliases = parser_aliases.add_subparsers(help="What you want to do.", dest="command")
    # parser_aliases_list = subparsers_aliases.add_parser('list', help='List registered aliases.')
    subparsers_aliases.add_parser('list', help='List registered aliases.')
    parser_aliases_add = subparsers_aliases.add_parser('add', help='Add a new alias.')
    parser_aliases_add.add_argument('domain_id', action='store',
                                    help='The ID of the domain to which the alias belongs.')
    parser_aliases_add.add_argument('source', action='store',
                                    help='The address whose incoming mail will be redirected.')
    parser_aliases_add.add_argument('destination', action='store',
                                    help='The address to which incoming mail will be redirected.')
    parser_aliases_remove = subparsers_aliases.add_parser('remove', help='Add a new alias.')
    parser_aliases_remove.add_argument('key', help='The ID of the alias to remove.', action='store')
    parser_aliases_edit = subparsers_aliases.add_parser('edit', help='Edit an alias.')
    parser_aliases_edit.add_argument('key', help='The ID of the alias to edit.', action='store')
    parser_aliases_edit.add_argument('--domain_id', action='store',
                                    help='The ID of the domain to which the alias belongs.')
    parser_aliases_edit.add_argument('--source', action='store',
                                    help='The address whose incoming mail will be redirected.')
    parser_aliases_edit.add_argument('--destination', action='store',
                                    help='The address to which incoming mail will be redirected.')


    parser.add_argument('--no-gui', action='store_true')


    return parser


def parse_args_cli(args: argparse.Namespace):
    """Run the command based on the arguments."""

    try:
        if args.area == 'domains':
            if args.command == 'list':
                db = core.MailAdminDatabase()
                db.print_domains()
            elif args.command == 'add':
                db = core.MailAdminDatabase()
                name = args.name
                domain = db.get_domain(0)
                domain.name = name
                db.commit_domain(domain)
            elif args.command == 'remove':
                db = core.MailAdminDatabase()
                key = args.key
                if args.by_name:
                    domain = db.get_domain_by_name(key)
                    db.delete_domain(domain.id)
                else:
                    db.delete_domain(int(key))
            elif args.command == 'edit':
                db = core.MailAdminDatabase()
                key = args.key
                if args.by_name:
                    domain = db.get_domain_by_name(key)
                else:
                    domain = db.get_domain(int(key))

                domain.name = args.new_name
                db.commit_domain(domain)

        elif args.area == 'users':
            if args.command == 'list':
                db = core.MailAdminDatabase()
                db.print_users()
            elif args.command == 'add':
                db = core.MailAdminDatabase()
                domain_id = int(args.domain_id)
                email = args.email
                pass1 = getpass('Enter a password:\n')
                pass2 = getpass('Reenter the password:\n')
                if pass1 != pass2:
                    print("The passwords do not match. Try again.")
                else:
                    user = db.get_user(0)
                    user.email = email
                    user.domain_id = domain_id
                    user.password = pass1
                    db.commit_user(user)
            elif args.command == 'remove':
                db = core.MailAdminDatabase()
                key = args.key
                if args.by_email:
                    user = db.get_user_by_email(key)
                    db.delete_user(user.id)
                else:
                    db.delete_user(int(key))
            elif args.command == 'edit':
                db = core.MailAdminDatabase()
                key = args.key
                if args.by_email:
                    user = db.get_user_by_email(key)
                else:
                    user = db.get_user(int(key))

                if args.domain_id:
                    user.domain_id = args.domain_id
                if args.new_email:
                    user.email = args.new_email
                if args.change_password:
                    pass1 = getpass('Enter a password:\n')
                    pass2 = getpass('Reenter the password:\n')
                    if pass1 != pass2:
                        print("The passwords do not match. Try again.")
                    else:
                        user.password = pass1
                db.commit_user(user)
        elif args.area == 'aliases':
            if args.command == 'list':
                db = core.MailAdminDatabase()
                db.print_aliases()
            elif args.command == 'remove':
                db = core.MailAdminDatabase()
                db.delete_alias(int(args.key))
            elif args.command == 'add':
                db = core.MailAdminDatabase()
                new_alias = db.get_alias(0)
                new_alias.domain_id = int(args.domain_id)
                new_alias.source = args.source
                new_alias.destination = args.destination
                db.commit_alias(new_alias)
            elif args.command == 'edit':
                db = core.MailAdminDatabase()
                alias = db.get_alias(int(key))
                if args.domain_id:
                    user.domain_id = int(args.domain_id)
                if args.source:
                    user.source = args.source
                if args.destination:
                    user.destination = args.destination
                db.commit_alias(alias)
    except core.DatabaseException as exc:
        print("ERROR:",exc)

if __name__ == '__main__':
    cli_parser = create_parser()
    cli_args = cli_parser.parse_args()
    parse_args_cli(cli_args)
