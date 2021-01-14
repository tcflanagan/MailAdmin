# MailAdmin
A simple command-line and gui interface for administering the user and domain database
for a Postfix- and Dovecot-based mail server configured following the guide at
[Linode](https://www.linode.com/docs/guides/email-with-postfix-dovecot-and-mysql/).

It is written in Python and depends on the `pymysql` and `wxPython` packages. In Debian 10, these
can be installed using

    $ sudo apt-get install python3-pymysql python3-wxgtk4.0

To create a server administrator user with the ability to modify the mail server database, do
the following:
1. Log in to MySQL as root

       $ sudo mysql

2. Create a new user

       > CREATE USER 'mailadmin' IDENTIFIED BY 'password';

3. Grant the user privileges on the mail server database

       > GRANT SELECT, UPDATE, INSERT, DELETE ON mailserver.* TO 'mailadmin'@'localhost';

The `mailadmin.conf` configuration file is already set with the values used in the guide linked
above and the steps in the preceding paragraph, though you will (hopefully) have to change the
value of password.

Then, to run the program, simply execute MailAdmin in the source directory. By default, it will
try to load the GUI version. If you execute it from a terminal, supply the `--no-gui` flag
to use the CLI version.