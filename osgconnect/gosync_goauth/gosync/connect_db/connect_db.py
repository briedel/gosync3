from __future__ import print_function
import psycopg2
import logging as log


class connect_db(object):
    def __init__(self, config):
        self.config = config
        self.connection = psycopg2.connect(
            host=self.config["connect_db"]["host"],
            user=self.config["connect_db"]["user"],
            password=self.config["connect_db"]["password"],
            dbname=self.config["connect_db"]["dbname"])
        self.cursor = self.connection.cursor()

    def __del__(self):
        self.connection.close()

    def get_member_count(self, group_name):
        with self.cursor as c:
            c.execute("""SELECT num_members
                         FROM groups
                         WHERE short_name=%s""",
                      (group_name,))
            mem_count = c.fetchall()[0][0]
        return mem_count

    def get_group_id(self, group_name):
        with self.cursor as c:
            c.execute("""SELECT id
                         FROM groups
                         WHERE short_name=%s""",
                      (group_name,))
            mem_id = c.fetchall()[0][0]
        return mem_id

    def get_member_id(self, username):
        with self.cursor as c:
            c.execute("""SELECT id
                         FROM users
                         WHERE username=%s""",
                      (username,))
            user_id = c.fetchall()[0][0]
        return user_id

    def add_group_membership(self, group_id, member_id):
        if isinstance(group_id, str):
            group_id = self.get_group_id(group_id)
        if isinstance(member_id, str):
            member_id = self.get_member_id(member_id)
        if not isinstance(group_id, int) or not group_id.isdigit():
            log.fatal()
            raise RuntimeError()
        if not isinstance(member_id, int) or not member_id.isdigit():
            log.fatal()
            raise RuntimeError()
        with self.cursor as c:
            c.execute("""INSERT INTO
                         groupmembers (group_id, user_id)
                         VALUES
                         (%s, %s)""",
                      (group_id, member_id))

    def get_group_members(self, group_id):
        with self.cursor as c:
            c.execute("""SELECT u.username
                         FROM users u
                         INNER JOIN groupmembers gm
                         ON gm.user_id = u.id
                         WHERE gm.group_id = %s""",
                      (group_id,))
            group_members = c.fetchall()[0]
        return group_members

    def get_anything_new(self, table, time_period=5 * 60):
        raise NotImplementedError()

    def add_member(self, member):
        with self.cursor as c:
            c.execute("""INSERT INTO users
                         (username, name, globus_uuid,
                          id_provider, email, organization,
                          unix_id, ssh_key)
                          VALUES
                          (%s, %s, %s,
                           %s, %s, %s,
                           %s, %s)""",
                      member)

    def add_alternate_identity(self, alternate_id):
        with self.cursor as c:
            sql = """INSERT INTO users
                     (username, name, globus_uuid,
                      id_provider, email, organization,
                      unix_id, ssh_key)
                      VALUES
                     (%s, %s, %s,
                      %s, %s, %s,
                      %s, %s)"""
            c.execute(sql,
                      (alternate_id["username"],))

    def add_identity_mapping(self, globus_member_id, alternate_id):
        raise NotImplementedError()

    def add_group(self, group):
        with self.cursor as c:
            sql = """INSERT INTO groups
                     (name, short_name, discipline,
                      other_discipline, pi, pi_email,
                      pi_organization, pi_department,
                      join_date, contact_name, contact_email,
                      phone_number, description, num_members,
                      parent_org, approved, globus_uuid,
                      unix_id)
                      VALUES
                      (%s, %s, %s,
                       %s, %s, %s,
                       %s, %s,
                       %s, %s, %s,
                       %s, %s, %s,
                       %s, %s, %s,
                       %s)"""
            c.execute(sql,
                      (group["name"], group["short_name"],
                       group["discipline"],
                       group["other_discipline"], group["pi"],
                       group["pi_email"], group["pi_organization"],
                       group["pi_department"], group["join_date"],
                       group["contact_name"], group["contact_email"],
                       group["phone_number"], group["description"],
                       group["num_members"], group["parent_org"],
                       group["approved"], group["globus_uuid"],
                       group["unix_id"]
                       ))

    def update_group_value(self, group, value):
        with self.cursor as c:
            sql = """UPDATE groups
                     SET %s = %s
                     WHERE groups.short_name = %s"""
            c.execute(sql, (value[0], value[1], group["short_name"]))

    def add_group_tree_mapping(self, parent_group, child_group):
        raise NotImplementedError()

    def get_approved_users_groups(self):    
        raise NotImplementedError()

    def get_approved_users(self):
        raise NotImplementedError()

    def get_groups(self, users=None):
        raise NotImplementedError()
