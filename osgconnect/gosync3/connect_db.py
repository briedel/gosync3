from __future__ import print_function
import os
import psycopg2
import psycopg2.extras
from collections import defaultdict
from util import sanitize_phone_number
from psycopg2.extensions import AsIs
import logging as log


class connect_db(object):
    def __init__(self, config):
        self.config = config
        self.connection = psycopg2.connect(
            user=self.config["connect_db"]["user"],
            password=self.config["connect_db"]["secret"],
            dbname=self.config["connect_db"]["db_name"])
        self.dict_cursor = psycopg2.extras.DictCursor

    def __del__(self):
        self.connection.close()

    def get_member_count(self, group_name):
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """SELECT num_members FROM groups WHERE short_name=%s"""
                c.execute(sql, (group_name,))
                mem_count = c.fetchall()
                if group_name != "old.ConnectTrain":
                    print(mem_count[0][0])
        return mem_count

    def get_unix_id(self, table, name):
        if table == "groups":
            column = "short_name"
        else:
            column = "username"
        with self.connection as conn:
            with conn.cursor(cursor_factory=self.dict_cursor) as c:
                sql = """SELECT unix_id FROM %(table)s WHERE %(column)=%s"""
                c.execute(sql, {"table": AsIs(table), "column": column})
                unix_id = c.fetchall()["unix_id"]
        return unix_id

    def get_group_id(self, group_name):
        return get_unix_id("groups", group_name)

    def get_member_id(self, username):
        return get_unix_id("users", username)

    def get_group_members(self, group_name):
        return self.get_group_line_info(
            group_name,
            list_group_members=True)[0]["array_agg"]

    def get_sub_groups(self, top_level_group):
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """SELECT short_name
                         FROM groups
                         WHERE (parent_org = %(group)s)
                         OR (name = %(group)s)"""
                c.execute(sql, {"group": top_level_group})
                groups = c.fetchall()
                groups = [group[0] for group in groups]
        return groups

    def get_group_line_info(self, group_name, get_sub_groups=False,
        list_group_members=False):
        with self.connection as conn:
            with conn.cursor(cursor_factory=self.dict_cursor) as c:
                if list_group_members:
                    sql = """SELECT g.short_name, g.unix_id, 
                                    array_agg(u.username, 
                                              ',' ORDER BY u.username) """
                else:
                    sql = """SELECT g.short_name, g.unix_id,
                                    string_agg(u.username,
                                               ',' ORDER BY u.username) """
                sql += """FROM users u
                          JOIN groupmembers gm
                          ON gm.user_id = u.id
                          JOIN groups g
                          ON gm.group_id = g.id """
                # TODO: Worry about root group?
                if (get_sub_groups and
                   group_name == self.config["globus"]["root_group"]):
                    sql += """GROUP BY 1, 2"""
                    sql_str = c.mogrify(sql)
                    c.execute(sql)
                if not get_sub_groups:
                    sql += """WHERE g.short_name = %s GROUP BY 1, 2"""
                    sql_str = c.mogrify(sql, (group_name,))
                    c.execute(sql, (group_name,))
                else:
                    sql += """WHERE ((g.short_name = %s) 
                              OR (g.parent_org = %s)) 
                              GROUP BY 1, 2"""
                    sql_str = c.mogrify(sql, (group_name,group_name))
                    c.execute(sql, (group_name, group_name))
                log.debug("Executing query: %s", sql_str)
                group_info = c.fetchall()
        group_info = [dict(row) for row in group_info]
        return group_info

    def get_user_sql_base(self):
        return """SELECT u.username, g.short_name, u.unix_id, u.name,
                         u.login_shell, u.email, u.ssh_key
                  FROM users u"""

    def get_group_user_sql(self):
        return """JOIN groupmembers gm
                  ON gm.user_id = u.id
                  JOIN groups g
                  ON gm.group_id = g.id"""

    def get_user_info(self,
                      username=None,
                      group_name=None,
                      get_sub_groups=False):
        # TODO: errors about inputs
        with self.connection as conn:
            with conn.cursor(cursor_factory=self.dict_cursor) as c:
                sql = self.get_user_sql_base()
                if (group_name is not None and
                   group_name != self.config["globus"]["root_group"]):
                    sql += self.get_group_user_sql()
                    sql += """WHERE g.short_name = %s """
                    if (get_sub_groups and
                       group_name in self.config[
                            "globus"]["top_level_groups"]):
                        sql += """OR (g.parent_org = %s)"""
                        c.execute(sql, (group_name, group_name))
                    else:
                        c.execute(sql, (group_name,))
                elif username is not None:
                    sql += "WHERE u.username = %s"
                    c.execute(sql, (username,))
                else:
                    c.execute(sql)
                user_info = c.fetchall()
        return user_info

    def get_new_approved_users(self):
        with self.connection as conn:
            with conn.cursor(cursor_factory=self.dict_cursor) as c:
                sql = self.get_user_sql_base()
                sql += self.get_group_user_sql()
                sql += """WHERE u.status = 'Approved'"""
                c.execute(sql)
                users = c.fetchall()
        return users

    def get_provisioned_users(self):
        with self.connection as conn:
            with conn.cursor(cursor_factory=self.dict_cursor) as c:
                sql = self.get_user_sql_base()
                sql += self.get_group_user_sql()
                sql += """WHERE ((u.status = 'SSHKeyMissing') 
                          OR (u.status = 'Provisioned'))"""
                c.execute(sql)
                users = c.fetchall()
        return users

    def check_collision(self, table, value_name, value):
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """SELECT * FROM %(table)s
                         WHERE %(value_name)s = %(value)s"""
                c.execute(sql,
                          {"table": AsIs(table),
                           "value_name": AsIs(value_name),
                           "value": value})
                if c.fetchone() is None:
                    return False
                else:
                    return True

    def check_unixid_collision(self, table, unix_id):
        return self.check_collision(table, "unix_id", unix_id)

    def get_anything_new(self, table, time_period=5 * 60):
        raise NotImplementedError()

    def edit_user_info(self, user, new_info):
        raise NotImplementedError()

    def edit_group_info(self, group, new_info):
        raise NotImplementedError()

    def add_group_membership(self, group, users):
        with self.connection as conn:
            with conn.cursor() as c:
                if not isinstance(users, list):
                    users = list(users)
                if isinstance(group, dict):
                    group = group["short_name"]
                for user in users:
                    if user == {}:
                        log.debug("Empty user")
                        continue
                    log.debug("Adding user %s to group %s",
                              group, user["username"])
                    # sql = """INSERT INTO groupmembers (group_id, user_id)
                    #          SELECT g.id, u.id
                    #          FROM groups g, users u
                    #          WHERE NOT EXISTS
                    #          ((SELECT * FROM groupmembers WHERE
                    #           groupmembers.group_id = g.id AND
                    #           groupmembers.user_id = u.id) AND
                    #           (g.short_name = %s AND u.username = %s))"""
                    sql = """INSERT INTO groupmembers (group_id, user_id)
                             SELECT g.id, u.id
                             FROM groups g, users u
                             WHERE (g.short_name = %s AND u.username = %s)
                             ON CONFLICT (group_id, user_id) DO NOTHING"""
                    c.execute(sql, (group, user["username"]))

    def add_new_member(self, member, safety=False):
        while self.check_unixid_collision("users", member["unix_id"]):
            log.debug("Unix UID collision for user %s", member["username"])
            member["unix_id"] += 1
        log.debug("Adding user %s", member["username"])
        member["service_account"] = service_account
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """INSERT INTO users
                         (username, name, globus_uuid,
                          id_provider, email, discipline,
                          institution, department, organization,
                          phone_number, unix_id, ssh_key, status, 
                          service_account, login_shell)
                         VALUES
                         (%(username)s, %(name)s, %(globus_uuid)s,
                          %(id_provider)s, %(email)s, %(discipline)s,
                          %(institution)s, %(department)s, %(organization)s,
                          %(phone_number)s, %(unix_id)s, %(ssh_key)s,
                          %(status)s)
                         ON CONFLICT (globus_uuid) DO NOTHING"""
                c.execute(sql, member)

    def add_linked_identity(self, linked_id):
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """INSERT INTO users
                         (username, name, globus_uuid,
                          id_provider, email, organization,
                          ssh_key)
                         VALUES
                         (%(username)s, %(name)s, %(globus_uuid)s,
                          %(id_provider)s, %(email)s, %(organization)s,
                          %(ssh_key)s)
                         ON CONFLICT (globus_uuid) DO NOTHING"""
                c.execute(sql, linked_id)

    def convert_globus_id_connect_db(self,
                                     globus_id, default_keys=None):
        if default_keys is None:
            log.fatal("Need default keys for conversion")
            raise RuntimeError()
        convert_dict_keys = {
            "identity_id": "globus_uuid",
            "full_name": "name",
            "organization": "organization",
            "phone": "phone_number",
            "field_of_science": "discipline"}
        connect_member = defaultdict(None).fromkeys(default_keys)
        for key, values in globus_id.iteritems():
            if key in convert_dict_keys.keys():
                connect_member[convert_dict_keys[key]] = values
            elif key == "ssh_pubkeys":
                connect_member["ssh_key"] = ""
                for v in values:
                    connect_member["ssh_key"] += v["ssh_key"] + "\n"
            elif key == "custom_fields":
                for k, v in values.iteritems():
                    if k == "phone":
                        v = sanitize_phone_number(v)
                    if k in convert_dict_keys.keys():
                        connect_member[convert_dict_keys[k]] = v
                    else:
                        connect_member[k] = v
            else:
                connect_member[key] = values
        return connect_member

    def convert_linked_id_globus_connect_db(self, linked_id):
        default_keys = ["username", "name", "globus_uuid", "id_provider",
                        "email", "organization", "ssh_key"]
        connect_member = self.convert_globus_id_connect_db(
            linked_id, default_keys=default_keys)
        return connect_member

    def convert_member_globus_connect_db(self, globus_id):
        default_keys = ["username", "name", "globus_uuid", "id_provider",
                        "email", "discipline", "institution", "department",
                        "organization", "phone_number", "unix_id", "ssh_key",
                        "status"]
        connect_member = self.convert_globus_id_connect_db(
            globus_id, default_keys=default_keys)
        return connect_member

        # convert_dict_keys = {
        #     "identity_id": "globus_uuid",
        #     "full_name": "name",
        #     "organization": "organization",
        #     "phone": "phone_number",
        #     "field_of_science": "discipline"
        # }
        # default_keys = ["username", "name", "globus_uuid",
        #                 "id_provider", "email", "discipline",
        #                 "institution", "department", "organization",
        #                 "phone_number", "unix_id", "ssh_key", "status"]
        # connect_member = defaultdict(None).fromkeys(default_keys)
        # for key, values in globus_member.iteritems():
        #     if key in convert_dict_keys.keys():
        #         connect_member[convert_dict_keys[key]] = values
        #     elif key == "ssh_pubkeys":
        #         connect_member["ssh_key"] = ""
        #         for v in values:
        #             connect_member["ssh_key"] += v["ssh_key"] + "\n"
        #     elif key == "custom_fields":
        #         for k, v in values.iteritems():
        #             if k == "phone":
        #                 v = sanitize_phone_number(v)
        #             if k in convert_dict_keys.keys():
        #                 connect_member[convert_dict_keys[k]] = v
        #             else:
        #                 connect_member[k] = v
        #     else:
        #         connect_member[key] = values
        # return connect_member

    def add_identity_mapping(self, globus_member_id, alternate_id):
        raise NotImplementedError()

    def add_new_group(self, group, safety=True):
        while self.check_unixid_collision("groups", group["unix_id"]):
            group["unix_id"] += 1
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """INSERT INTO groups
                         (name, short_name, discipline,
                          other_discipline, pi, pi_email,
                          pi_organization, pi_department,
                          join_date, contact_name, contact_email,
                          phone_number, description, num_members,
                          parent_org, approved, globus_uuid,
                          unix_id)
                         VALUES
                         (%(name)s, %(short_name)s, %(discipline)s,
                           %(other_discipline)s, %(pi)s, %(pi_email)s,
                           %(pi_organization)s, %(pi_department)s,
                           %(join_date)s, %(contact_name)s, %(contact_email)s,
                           %(phone_number)s, %(description)s, %(num_members)s,
                           %(parent_org)s, %(approved)s, %(globus_uuid)s,
                           %(unix_id)s)
                         ON CONFLICT (globus_uuid) DO NOTHING"""
                c.execute(sql, group)

    def update_group_value(self, group, value_name, value):
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """UPDATE groups
                         SET %(value_name)s = %(value)s
                         WHERE groups.short_name = %(group_name)s"""
                c.execute(sql, {"value_name": AsIs(value_name),
                                "value": value,
                                "group_name": group["short_name"]})

    def add_group_tree_mapping(self, parent_group, child_group):
        with self.connection as conn:
            with conn.cursor() as c:
                sql = """INSERT INTO grouptree
                         SELECT p.id, c.id
                         FROM groups p, groups c,
                         WHERE p.short_name = %s
                         AND c.short_name = %s"""
                c.execute(sql, (parent_group["short_name"],
                                child_group["short_name"]))

    """
    Section to get things out of the database in the usual formats
    """

    def generate_group_line(self, group_info):
        # Format for /etc/group file:
        # group_name:password:guid:member_list_as_csv
        log.debug("Group Info: %s", group_info)
        group_line = [group_info["short_name"], "x",
                      str(group_info["unix_id"]), group_info["string_agg"]]
        log.debug("Group Line: %s", group_line)
        return (":").join(group_line)

    def generate_group_file(self, group_name=None, get_sub_groups=True):
        # get the group_line for a set of group_name
        groups = ["users:x:1000:"]
        if (group_name is not None and
           group_name in self.config["globus"]["top_level_groups"]):
            groups_info = self.get_group_line_info(
                group_name=group_name,
                get_sub_groups=get_sub_groups)
        elif group_name is not None:
            groups_info = self.get_group_line_info(group_name=group_name)
        else:
            groups_info = self.get_group_line_info(
                group_name=self.config["globus"]["root_group"],
                get_sub_groups=get_sub_groups)
        groups += [self.generate_group_line(grp_info)
                   for grp_info in groups_info]
        return ("\n").join(groups)

    def generate_passwd_line(self, user_info):
        # Format for /etc/passwd file:
        # username:password:uid:default_guid:full_name:homedir:login_shell
        pass_line = [user_info["username"], "x", str(user_info["unix_id"]),
                     self.config["users"]["default_group"], user_info["name"],
                     os.path.join("/home", user_info["username"]),
                     user_info["login_shell"]]
        return (":").join(pass_line)

    def generate_passwd_file(self, group_name=None, get_sub_groups=True):
        if (group_name is not None and
           group_name in self.config["globus"]["top_level_groups"]):
            users_info = self.get_user_info(
                group_name=group_name,
                get_sub_groups=get_sub_groups)
        elif group_name is not None:
            users_info = self.get_user_info(group_name=group_name)
        else:
            users_info = self.get_group_line_info(
                group_name=self.config["globus"]["root_group"],
                get_sub_groups=get_sub_groups)
        users = [self.generate_passwd_line(usr_info)
                 for usr_info in users_info]
        return ("\n").join(users)

    def get_to_be_provisioned_users(self):
        raise NotImplementedError()
