#!/usr/bin/env python3
"""Graphical interface for administering the mail server database.

A simple graphical interface for inspecting and manipulating the database associated
with a Postfix- and Dovecot-based mail server configured according to the instructions
from Linode (https://www.linode.com/docs/guides/email-with-postfix-dovecot-and-mysql/).
"""

from copy import copy
from typing import List, Union

import wx

import mailadmin_core as core

# pylint: disable=unsubscriptable-object,too-many-ancestors,too-few-public-methods

class EntityPanel(wx.Panel):
    """Panel for displaying a list and add/edit/remove buttons for domains, users, and aliases.

    Attributes
    ----------
    item_ctl : wx.ListCtrl
        The list of entities displayed by the panel.
    btn_add : wx.Button
        The button to add entities.
    btn_edit : wx.Button
        The button to edit entities.
    btn_remove : wx.Button
        The button to remove entities.
    """

    def __init__(self, parent, label: str, headings: List[str],
                 initial_data: Union[List[str], List[List[str]]],
                 add_handler=None, edit_handler=None, remove_handler=None):
        """Initialize the panel.

        Parameters
        ----------
        parent : wx.Window
            The parent of this panel.
        label : str
            The label for the static box.
        headings : list of str
            The headings for the columns.
        initial_data : list of str or list of list of str
            The initial data. The outermost list should have one element for each row. Each
            element should be either the value of that row or, if there are multiple columns, a
            list of strings with values for each column.
        add_handler : callable
            The event handler to call when the Add button is clicked.
        edit_handler : callable
            The event handler to call when the Edit button is clicked.
        remove_handler : callable
            The event handler to call when the Delete button is clicked.
        """
        super().__init__(parent)

        static_box = wx.StaticBox(self, wx.ID_ANY, label)
        static_box_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)

        inner_sizer = wx.BoxSizer(wx.VERTICAL)

        self.item_ctl = wx.ListCtrl(static_box, wx.ID_ANY, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)

        for item in headings:
            self.item_ctl.AppendColumn(item)

        for item in initial_data:
            if isinstance(item, str):
                item = [item]
            self.item_ctl.Append(item)

        self.item_ctl.SetMinSize(wx.Size(500, 100))
        self.item_ctl.Bind(wx.EVT_SIZE, self._on_resize)
        self.item_ctl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self.item_ctl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_select)

        btn_panel = wx.Panel(static_box, wx.ID_ANY)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_panel.SetSizer(btn_sizer)

        self.btn_add = wx.Button(btn_panel, wx.ID_ANY, 'Add')
        if add_handler:
            self.btn_add.Bind(wx.EVT_BUTTON, add_handler)
        btn_sizer.Add(self.btn_add, 0, wx.ALL, 5)
        self.btn_edit = wx.Button(btn_panel, wx.ID_ANY, 'Edit')
        self.btn_edit.Disable()
        if edit_handler:
            self.btn_edit.Bind(wx.EVT_BUTTON, edit_handler)
        btn_sizer.Add(self.btn_edit, 0, wx.ALL, 5)
        self.btn_remove = wx.Button(btn_panel, wx.ID_ANY, 'Remove')
        self.btn_remove.Disable()
        if remove_handler:
            self.btn_remove.Bind(wx.EVT_BUTTON, remove_handler)
        btn_sizer.Add(self.btn_remove, 0, wx.ALL, 5)

        inner_sizer.Add(self.item_ctl, 1, wx.EXPAND | wx.ALL, 5)
        inner_sizer.Add(btn_panel, 0, wx.ALIGN_RIGHT)

        static_box_sizer.Add(inner_sizer, 1, wx.EXPAND)
        self.SetSizerAndFit(static_box_sizer)


    def _on_resize(self, evt):
        rect = self.item_ctl.GetClientSize()
        num_cols = self.item_ctl.GetColumnCount()
        width = int(rect.width / num_cols)
        for i in range(num_cols):
            self.item_ctl.SetColumnWidth(i, width)
        evt.Skip()

    def _on_select(self, _):
        enable = self.item_ctl.GetSelectedItemCount() > 0
        self.btn_edit.Enable(enable)
        self.btn_remove.Enable(enable)

    def add_row(self, item: Union[str, List[str]]):
        """Add a row to the list.

        Parameters
        ----------
        item : str or list of str
            The column or list of columns to add.
        """
        if isinstance(item, str):
            item = [item]
        self.item_ctl.Append(item)

    def remove_row(self, index: int):
        """Remove a row from the list.

        Parameters
        ----------
        index : int
            The index of the row to remove.
        """
        self.item_ctl.DeleteItem(index)

    def edit_row(self, index: int, column: int, new_value: str):
        """Change the contents of a cell in the list.

        Parameters
        ----------
        index : int
            The index of the row to change.
        column : int
            The index of the column to change.
        new_value : str
            The value to insert into the list.
        """
        self.item_ctl.SetItem(index, column, new_value)

    def replace_all_rows(self, new_data):
        """Replace all contents of the list.

        Parameters
        ----------
        new_data : list of str or list of list of str
            The new rows to put into the table.
        """
        for item in new_data:
            if isinstance(item, str):
                item = [item]
            self.item_ctl.Append(item)


class EditDomainDialog(wx.Dialog):
    """A dialog for creating/editing domains.

    Attributes
    ----------
    data_name : wx.TextCtrl
        Input control for the domain name.
    """

    def __init__(self, parent, domain: core.Domain):
        if domain.id == 0:
            title = 'Add Domain'
        else:
            title = f'Edit Domain "{domain.name}"'

        super().__init__(parent, wx.ID_ANY, title)

        outer_panel = wx.Panel(self)
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_panel.SetSizer(outer_sizer)

        data_panel = wx.Panel(outer_panel, wx.ID_ANY)
        data_sizer = wx.FlexGridSizer(2, 5, 5)
        data_panel.SetSizer(data_sizer)
        data_sizer.AddGrowableCol(1, 1)

        data_sizer.Add(wx.StaticText(data_panel, wx.ID_ANY, 'Domain Name:'),
                       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.data_name = wx.TextCtrl(data_panel, wx.ID_ANY)
        self.data_name.SetValue(domain.name)
        self.data_name.SetMinSize(wx.Size(200, -1))
        data_sizer.Add(self.data_name, 1, wx.EXPAND)

        button_panel = wx.Panel(outer_panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_panel.SetSizer(button_sizer)

        btn_ok = wx.Button(button_panel, wx.ID_OK, "Save")
        button_sizer.Add(btn_ok, 0, wx.ALL, 5)
        btn_cancel = wx.Button(button_panel, wx.ID_CANCEL, "Cancel")
        button_sizer.Add(btn_cancel, 0, wx.ALL, 5)

        outer_sizer.Add(data_panel, 1, wx.EXPAND | wx.ALL, 5)
        outer_sizer.Add(button_panel, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(outer_panel, 1, wx.EXPAND)

        self.SetSizerAndFit(vbox)

class EditUserDialog(wx.Dialog):
    """A dialog for editing users.

    Attributes
    ----------
    data_name : wx.TextCtrl
        The input control for the user name.
    data_domain : wx.Choice
        Input control for the domain name.
    data_pw1 : wx.TextCtrl
        Input control for the password.
    data_pw2 : wx.TextCtrl
        Input control for re-entering the password.
    """

    def __init__(self, parent, user: core.User, domains):

        domain_index = domains['ids'].index(user.domain_id)
        user_name = user.email.replace('@' + domains['names'][domain_index], '')

        if user.id == 0:
            pass_label = 'Enter Password:'
        else:
            pass_label = 'Enter Password (or blanks to leave password unchanged):'

        super().__init__(parent, wx.ID_ANY,
                         'Add User' if user.id == 0 else f'Edit User "{user_name}"')

        outer_panel = wx.Panel(self)
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_panel.SetSizer(outer_sizer)

        data_panel = wx.Panel(outer_panel, wx.ID_ANY)
        data_sizer = wx.FlexGridSizer(2, 5, 5)
        data_panel.SetSizer(data_sizer)
        data_sizer.AddGrowableCol(1, 1)

        data_sizer.Add(wx.StaticText(data_panel, wx.ID_ANY, 'User Name:'),
                       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.data_name = wx.TextCtrl(data_panel, wx.ID_ANY, value=user_name)
        self.data_name.SetMinSize(wx.Size(200, -1))
        data_sizer.Add(self.data_name, 1, wx.EXPAND)
        data_sizer.Add(wx.StaticText(data_panel, wx.ID_ANY, 'Domain:'),
                       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.data_domain = wx.Choice(data_panel, wx.ID_ANY, choices=domains['names'])
        self.data_domain.SetSelection(domain_index)
        data_sizer.Add(self.data_domain, 1, wx.EXPAND)

        pass_panel = wx.Panel(outer_panel, wx.ID_ANY)
        pass_sizer = wx.FlexGridSizer(1, 5, 5)
        pass_sizer.AddGrowableCol(0, 1)
        pass_panel.SetSizer(pass_sizer)

        pass_sizer.Add(wx.StaticText(pass_panel, wx.ID_ANY, pass_label), 0)
        self.data_pw1 = wx.TextCtrl(pass_panel, wx.ID_ANY, style=wx.TE_PASSWORD,
                                    value=(user.password or ''))
        pass_sizer.Add(self.data_pw1, 1, wx.EXPAND)
        pass_sizer.Add(wx.StaticText(pass_panel, wx.ID_ANY, 'Re-enter Password:'), 0)
        self.data_pw2 = wx.TextCtrl(pass_panel, wx.ID_ANY, style=wx.TE_PASSWORD,
                                    value=(user.password or ''))
        pass_sizer.Add(self.data_pw2, 1, wx.EXPAND)

        button_panel = wx.Panel(outer_panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_panel.SetSizer(button_sizer)

        button_sizer.Add(wx.Button(button_panel, wx.ID_OK, "Save"), 0, wx.ALL, 5)
        button_sizer.Add(wx.Button(button_panel, wx.ID_CANCEL, "Cancel"), 0, wx.ALL, 5)

        outer_sizer.Add(data_panel, 1, wx.ALL | wx.EXPAND, 5)
        outer_sizer.Add(pass_panel, 0, wx.ALL | wx.EXPAND, 5)
        outer_sizer.Add(button_panel, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(outer_panel, 1, wx.EXPAND)

        self.SetSizerAndFit(vbox)


class EditAliasDialog(wx.Dialog):
    """A dialog for creating/editing aliases.

    Attributes
    ----------
    data_domain : wx.Choice
        Input control for the domain.
    data_source : wx.TextCtrl
        Input control for the source email.
    data_destination : wx.TextCtrl
        Input countrol for the destination email.
    """

    def __init__(self, parent, alias: core.Alias, domains):
        if alias.id == 0:
            title = 'Add Alias'
        else:
            title = f'Edit Alias "{alias.source} to {alias.destination}"'

        super().__init__(parent, wx.ID_ANY, title)

        outer_panel = wx.Panel(self)
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_panel.SetSizer(outer_sizer)

        data_panel = wx.Panel(outer_panel, wx.ID_ANY)
        data_sizer = wx.FlexGridSizer(2, 5, 5)
        data_panel.SetSizer(data_sizer)
        data_sizer.AddGrowableCol(1, 1)

        domain_index = domains['ids'].index(alias.domain_id)

        data_sizer.Add(wx.StaticText(data_panel, wx.ID_ANY, 'Domain:'),
                       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.data_domain = wx.Choice(data_panel, wx.ID_ANY, choices=domains['names'])
        self.data_domain.SetSelection(domain_index)
        self.data_domain.SetMinSize(wx.Size(300, -1))
        data_sizer.Add(self.data_domain, 1, wx.EXPAND)
        data_sizer.Add(wx.StaticText(data_panel, wx.ID_ANY, 'Source Address:'),
                       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.data_source = wx.TextCtrl(data_panel, wx.ID_ANY, value=alias.source)
        data_sizer.Add(self.data_source, 1, wx.EXPAND)
        data_sizer.Add(wx.StaticText(data_panel, wx.ID_ANY, 'Destination Address:'),
                       0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        self.data_destination = wx.TextCtrl(data_panel, wx.ID_ANY, value=alias.destination)
        data_sizer.Add(self.data_destination, 1, wx.EXPAND)

        button_panel = wx.Panel(outer_panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_panel.SetSizer(button_sizer)

        btn_ok = wx.Button(button_panel, wx.ID_OK, "Save")
        button_sizer.Add(btn_ok, 0, wx.ALL, 5)
        btn_cancel = wx.Button(button_panel, wx.ID_CANCEL, "Cancel")
        button_sizer.Add(btn_cancel, 0, wx.ALL, 5)

        outer_sizer.Add(data_panel, 1, wx.EXPAND | wx.ALL, 5)
        outer_sizer.Add(button_panel, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(outer_panel, 1, wx.EXPAND)

        self.SetSizerAndFit(vbox)

class AppFrame(wx.Frame):
    """Main frame for the application."""

    def __init__(self, parent):
        super().__init__(parent, title='Mail User Manager', size=(600, 800))

        self.db = core.MailAdminDatabase()

        self.domains = self.db.get_domains()
        self.users = self.db.get_users()
        self.aliases = self.db.get_aliases()

        self.__init_interface()

    def __init_interface(self):

        outer_panel = wx.Panel(self)
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_panel.SetSizer(outer_sizer)

        main_panel = wx.Panel(outer_panel)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(main_sizer)

        self.domain_panel = EntityPanel(main_panel, 'Domains', ['Domain Name'],
                                        self.domains['names'],
                                        self._on_add_domain, self._on_edit_domain,
                                        self._on_delete_domain)

        self.user_panel = EntityPanel(main_panel, 'Users', ['Email Address'],
                                      self.users['emails'],
                                      self._on_add_user, self._on_edit_user,
                                      self._on_delete_user)

        self.alias_panel = EntityPanel(main_panel, 'Aliases', ['Source', 'Destination'],
                                       zip(self.aliases['sources'], self.aliases['destinations']),
                                       self._on_add_alias, self._on_edit_alias,
                                       self._on_delete_alias)

        button_panel = wx.Panel(main_panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_panel.SetSizer(button_sizer)

        close_button = wx.Button(button_panel, wx.ID_EXIT, 'Close')
        close_button.Bind(wx.EVT_BUTTON, self._on_close)
        button_sizer.Add(close_button, 0, wx.ALL, 5)

        main_sizer.Add(self.domain_panel, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.user_panel, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.alias_panel, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(button_panel, 0, wx.ALIGN_RIGHT)

        outer_sizer.Add(main_panel, 1, wx.EXPAND | wx.ALL, 5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(outer_panel, 1, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def _on_close(self, _):
        self.Destroy()

    def _on_add_domain(self, _, domain: core.Domain = None):
        domain = domain or self.db.get_domain(0)
        with EditDomainDialog(self, domain) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    domain.name = dlg.data_name.GetValue()

                    backup_domain = copy(domain)
                    self.db.commit_domain(domain)

                    self.domains['names'].append(domain.name)
                    self.domains['ids'].append(domain.id)
                    self.domain_panel.add_row(domain.name)
                except core.DatabaseException as exc:
                    wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                    self._on_add_domain(None, backup_domain)
            else:
                pass

    def _on_edit_domain(self, _, domain: core.Domain = None):
        item = self.domain_panel.item_ctl.GetFirstSelected()
        if item >= 0:
            domain_id = self.domains['ids'][item]
            domain = domain or self.db.get_domain(domain_id)
            with EditDomainDialog(self, domain) as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    try:
                        domain.name = dlg.data_name.GetValue()

                        backup_domain = copy(domain)
                        self.db.commit_domain(domain)

                        self.domains['names'][item] = domain.name
                        self.domain_panel.edit_row(item, 0, domain.name)
                    except core.DatabaseException as exc:
                        wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                        self._on_edit_domain(None, backup_domain)
                else:
                    pass

    def _on_delete_domain(self, _):
        item = self.domain_panel.item_ctl.GetFirstSelected()
        if item >= 0:
            domain_id = self.domains['ids'][item]
            with wx.MessageDialog(self,
                                  'Are you sure you want to delete the domain %s?'
                                    % self.domains["names"][item],
                                  'Confirm',
                                  wx.YES_NO | wx.NO_DEFAULT) as dlg:
                if dlg.ShowModal() == wx.ID_YES:
                    try:
                        self.db.delete_domain(domain_id)
                        self.domains['names'].pop(item)
                        self.domains['ids'].pop(item)
                        self.domain_panel.remove_row(item)
                    except core.DatabaseException as exc:
                        wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                else:
                    pass

    def _on_add_user(self, _, user: core.User = None):
        user = user or self.db.get_user(0)

        with EditUserDialog(self, user, self.domains) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    new_domain_index = dlg.data_domain.GetSelection()
                    user.domain_id = self.domains['ids'][new_domain_index]

                    new_username = dlg.data_name.GetValue()
                    new_domain_string = self.domains['names'][new_domain_index]
                    user.email = f'{new_username}@{new_domain_string}'

                    backup_user = copy(user)

                    if '@' in new_username:
                        raise core.DatabaseException('Username cannot contain an "@" character.')

                    new_pass1 = dlg.data_pw1.GetValue()
                    new_pass2 = dlg.data_pw2.GetValue()
                    if new_pass1 != new_pass2:
                        raise core.DatabaseException('Passwords must match.')
                    if len(new_pass1) == 0:
                        raise core.DatabaseException(
                            'A password is required (and must be at least 8 characters).')
                    user.password = new_pass1

                    self.db.commit_user(user)

                    self.users['ids'].append(user.id)
                    self.users['emails'].append(user.email)
                    self.users['domain_ids'].append(user.domain_id)
                    self.user_panel.add_row(user.email)

                except core.DatabaseException as exc:
                    wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                    self._on_add_user(None, backup_user)
            else:
                pass

    def _on_edit_user(self, _, user: core.User = None):
        index = self.user_panel.item_ctl.GetFirstSelected()
        if index >= 0:
            user_id = self.users['ids'][index]
            user = user or self.db.get_user(user_id)

            with EditUserDialog(self, user, self.domains) as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    try:
                        new_domain_index = dlg.data_domain.GetSelection()
                        user.domain_id = self.domains['ids'][new_domain_index]

                        new_username = dlg.data_name.GetValue()
                        new_domain_string = self.domains['names'][new_domain_index]
                        user.email = f'{new_username}@{new_domain_string}'

                        backup_user = copy(user)

                        new_pass1 = dlg.data_pw1.GetValue()
                        new_pass2 = dlg.data_pw2.GetValue()
                        if new_pass1 != new_pass2:
                            raise core.DatabaseException('Passwords must match.')
                        if len(new_pass1) > 0:
                            user.password = new_pass1
                        else:
                            user.password = None

                        self.db.commit_user(user)

                        self.users['ids'][index] = user.id
                        self.users['emails'][index] = user.email
                        self.users['domain_ids'][index] = user.domain_id
                        self.user_panel.edit_row(index, 0, user.email)

                    except core.DatabaseException as exc:
                        wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                        self._on_edit_user(None, backup_user)
                else:
                    pass


    def _on_delete_user(self, _):
        item = self.user_panel.item_ctl.GetFirstSelected()
        if item >= 0:
            user_id = self.users['ids'][item]
            with wx.MessageDialog(self,
                    f'Are you sure you want to delete the user {self.users["emails"][item]}?',
                    'Confirm',
                    wx.YES_NO | wx.NO_DEFAULT) as dlg:
                if dlg.ShowModal() == wx.ID_YES:
                    try:
                        self.db.delete_user(user_id)
                        self.users['emails'].pop(item)
                        self.users['ids'].pop(item)
                        self.users['domain_ids'].pop(item)
                        self.user_panel.remove_row(item)
                    except core.DatabaseException as exc:
                        wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                else:
                    pass


    def _on_add_alias(self, _, alias: core.Alias = None):
        alias = alias or self.db.get_alias(0)

        with EditAliasDialog(self, alias, self.domains) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    new_domain_index = dlg.data_domain.GetSelection()
                    alias.domain_id = self.domains['ids'][new_domain_index]

                    alias.source = dlg.data_source.GetValue()
                    alias.destination = dlg.data_destination.GetValue()

                    backup_alias = copy(alias)

                    self.db.commit_alias(alias)

                    self.aliases['ids'].append(alias.id)
                    self.aliases['sources'].append(alias.source)
                    self.aliases['destinations'].append(alias.destination)
                    self.aliases['domain_ids'].append(alias.domain_id)
                    self.alias_panel.add_row([alias.source, alias.destination])

                except core.DatabaseException as exc:
                    wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                    self._on_add_alias(None, backup_alias)
            else:
                pass


    def _on_edit_alias(self, _, alias: core.Alias = None):
        index = self.alias_panel.item_ctl.GetFirstSelected()
        if index >= 0:
            alias_id = self.aliases['ids'][index]
            alias = alias or self.db.get_alias(alias_id)

            with EditAliasDialog(self, alias, self.domains) as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    try:
                        new_domain_index = dlg.data_domain.GetSelection()
                        alias.domain_id = self.domains['ids'][new_domain_index]

                        alias.source = dlg.data_source.GetValue()
                        alias.destination = dlg.data_destination.GetValue()

                        backup_alias = copy(alias)

                        self.db.commit_alias(alias)

                        self.aliases['ids'][index] = alias.id
                        self.aliases['sources'][index] = alias.source
                        self.aliases['destinations'][index] = alias.destination
                        self.aliases['domain_ids'][index] = alias.domain_id
                        self.alias_panel.edit_row(index, 0, alias.source)
                        self.alias_panel.edit_row(index, 1, alias.destination)

                    except core.DatabaseException as exc:
                        wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                        self._on_edit_alias(None, backup_alias)
                else:
                    pass

    def _on_delete_alias(self, _):
        item = self.alias_panel.item_ctl.GetFirstSelected()
        if item >= 0:
            alias_id = self.aliases['ids'][item]
            with wx.MessageDialog(self,
                    'Are you sure you want to delete the alias ' + self.aliases["source"][item] +
                    ' to ' + self.aliases['destination'][item] + '?',
                    'Confirm',
                    wx.YES_NO | wx.NO_DEFAULT) as dlg:
                if dlg.ShowModal() == wx.ID_YES:
                    try:
                        self.db.delete_alias(alias_id)
                        self.aliases['sources'].pop(item)
                        self.aliases['destinations'].pop(item)
                        self.aliases['ids'].pop(item)
                        self.aliases['domain_ids'].pop(item)
                        self.alias_panel.remove_row(item)
                    except core.DatabaseException as exc:
                        wx.MessageBox(str(exc), 'Error', wx.ICON_ERROR)
                else:
                    pass

if __name__ == '__main__':
    app = wx.App()
    frame = AppFrame(None)
    frame.Show()
    app.MainLoop()
