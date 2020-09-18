# client = MongoClient("localhost")
# db = client["unigames_webapp_db"]
# collection = db["Items"]
#
# collection.insert_one({"test": "test"})

from flask import Flask
from flask_pymongo import PyMongo

from app.database_impl.attrib_options import AttributeOption, AttributeTypes
from app.database_impl.items_instances import Item, Instance
from app.database_impl.relations import RelationOption, Relation
from app.database_impl.roles import Role, Permissions
from app.database_impl.tags import Tag, TagReference
from app.database_impl.users import User
from app.search_parser import search_string_to_mongodb_query


class DatabaseManager:
    mongo = None

    def __init__(self, app: Flask):
        app.config["MONGO_URI"] = "mongodb://localhost:27017/unigames_webapp_db"

        self.mongo = PyMongo(app)
        Tag.init_indices(self.mongo)
        AttributeOption.init_indices(self.mongo)
        Item.init_indices(self.mongo)
        Instance.init_indices(self.mongo)
        Role.init_indices(self.mongo)
        RelationOption.init_indices(self.mongo)
        Relation.init_indices(self.mongo)

    def test(self):
        # create a book tag
        book_tag = Tag.search_for_by_name(self.mongo, "Book")
        if book_tag is None:
            book_tag = Tag("Book", [])
            book_tag.write_to_db(self.mongo)

        # create a multiplayer tag
        multiplayer_tag = Tag.search_for_by_name(self.mongo, "Multiplayer")
        if multiplayer_tag is None:
            multiplayer_tag = Tag("Multiplayer", [])
            multiplayer_tag.write_to_db(self.mongo)

        # create a player 1 tag
        players_tag_1 = Tag.search_for_by_name(self.mongo, "Players: 1")
        if players_tag_1 is None:
            players_tag_1 = Tag("Players: 1", [])
            players_tag_1.write_to_db(self.mongo)

        # create a player 2 tag
        players_tag_2 = Tag.search_for_by_name(self.mongo, "Players: 2")
        if players_tag_2 is None:
            players_tag_2 = Tag("Players: 2", [TagReference(multiplayer_tag)])
            players_tag_2.write_to_db(self.mongo)

        # create a player 3 tag
        players_tag_3 = Tag.search_for_by_name(self.mongo, "Players: 3")
        if players_tag_3 is None:
            players_tag_3 = Tag("Players: 3", [TagReference(multiplayer_tag)])
            players_tag_3.write_to_db(self.mongo)

        # create a player 4 tag
        players_tag_4 = Tag.search_for_by_name(self.mongo, "Players: 4")
        if players_tag_4 is None:
            players_tag_4 = Tag("Players: 4", [TagReference(multiplayer_tag)])
            players_tag_4.write_to_db(self.mongo)

        # create a player 5 tag
        players_tag_5 = Tag.search_for_by_name(self.mongo, "Players: 5")
        if players_tag_5 is None:
            players_tag_5 = Tag("Players: 5", [TagReference(multiplayer_tag)])
            players_tag_5.write_to_db(self.mongo)

        # create a player 6 tag
        players_tag_6 = Tag.search_for_by_name(self.mongo, "Players: 6")
        if players_tag_6 is None:
            players_tag_6 = Tag("Players: 6", [TagReference(multiplayer_tag)])
            players_tag_6.write_to_db(self.mongo)

        # create a damaged tag
        damaged_tag = Tag.search_for_by_name(self.mongo, "Damaged")
        if damaged_tag is None:
            damaged_tag = Tag("Damaged", [])
            damaged_tag.write_to_db(self.mongo)

        # create a borrowed out tag
        borrowed_out_tag = Tag.search_for_by_name(self.mongo, "Borrowed Out")
        if borrowed_out_tag is None:
            borrowed_out_tag = Tag("Borrowed Out", [])
            borrowed_out_tag.write_to_db(self.mongo)

        # create a None tag (all root tags point to this tag for easier management)
        root_tag = Tag.search_for_by_name(self.mongo, "None")
        if root_tag is None:
            root_tag = Tag("None", [])
            root_tag.write_to_db(self.mongo)

        # create an attribute for name
        item_name_attrib = AttributeOption.search_for_by_name(self.mongo, "name")
        if item_name_attrib is None:
            item_name_attrib = AttributeOption("name", AttributeTypes.SingleLineString)
            item_name_attrib.write_to_db(self.mongo)

        # create an attribute for author
        item_author_attrib = AttributeOption.search_for_by_name(self.mongo, "author")
        if item_author_attrib is None:
            item_author_attrib = AttributeOption("author", AttributeTypes.SingleLineString)
            item_author_attrib.write_to_db(self.mongo)

        # create an attribute for description
        item_description_attrib = AttributeOption.search_for_by_name(self.mongo, "description")
        if item_description_attrib is None:
            item_description_attrib = AttributeOption("description", AttributeTypes.MultiLineString)
            item_description_attrib.write_to_db(self.mongo)

        # search for the uuid attribute
        instance_uuid_attrib = AttributeOption.search_for_by_name(self.mongo, "uuid")
        # if none returned, create a new uuid attribute
        if instance_uuid_attrib is None:
            instance_uuid_attrib = AttributeOption("uuid", AttributeTypes.SingleLineString)
            instance_uuid_attrib.write_to_db(self.mongo)

        # search for the Damage Report attribute
        instance_damage_report_attrib = AttributeOption.search_for_by_name(self.mongo, "Damage Report")
        # if none returned, create a Damage Report attribute
        if instance_damage_report_attrib is None:
            instance_damage_report_attrib = AttributeOption("Damage Report", AttributeTypes.MultiLineString)
            instance_damage_report_attrib.write_to_db(self.mongo)

        # search for item by its name attribute
        bob_book_item = Item.search_for_by_attribute(self.mongo, item_name_attrib, "Bob's Grand Adventure")
        # create a new item if no search result returned
        if not bob_book_item:
            bob_book_item = Item({"name": "Bob's Grand Adventure", "description": "No description"},
                                 [
                                     TagReference(book_tag), TagReference(players_tag_3), TagReference(players_tag_4),
                                     TagReference(players_tag_5)
                                 ], [])

            bob_book_item.instances.append(Instance({"uuid": "109358180",
                                                     "Damage Report": "(4/5/2017): Page 57 has a small section of the top right corner torn off, no text missing, still serviceable"},
                                                    [TagReference(damaged_tag)]))
            bob_book_item.instances.append(Instance({"uuid": "109358181"}, []))

            bob_book_item.write_to_db(self.mongo)
        else:
            bob_book_item = bob_book_item[0]

        # recalculates all implied tags for the item and instances
        bob_book_item.recalculate_implied_tags(self.mongo, True)

        everyone_role = Role.search_for_by_name(self.mongo, "everyone")
        if everyone_role is None:  # -1 is overridden by everything, an 'everyone' is required for sake of a default
            everyone_role = Role("everyone", -1, {Permissions.CanEditItems: False, Permissions.CanEditUsers: False})
            everyone_role.write_to_db(self.mongo)

        admin_role = Role.search_for_by_name(self.mongo, "admin")
        if admin_role is None:  # 0 overrides everything
            admin_role = Role("admin", 0, {Permissions.CanEditItems: True, Permissions.CanEditUsers: True})
            admin_role.write_to_db(self.mongo)

        borrowing_item_relation = RelationOption.search_for_by_name(self.mongo, "Borrowing")
        if borrowing_item_relation is None:
            borrowing_item_relation = RelationOption("Borrowing", [TagReference(borrowed_out_tag)])
            borrowing_item_relation.write_to_db(self.mongo)

        matthew_user = User.search_for_by_display_name(self.mongo, "Matthew")
        if matthew_user is None:
            matthew_user = User("Matthew", [admin_role.id])
            matthew_user.write_to_db(self.mongo)

        inst_0_id = [inst for inst in bob_book_item.instances if inst.attributes["uuid"] == "109358180"][0].id
        inst_1_id = [inst for inst in bob_book_item.instances if inst.attributes["uuid"] == "109358181"][0].id

        matthew_bob_borrow_relation = Relation.search_for_by_instance_id(self.mongo, inst_1_id)
        if not matthew_bob_borrow_relation:
            matthew_bob_borrow_relation = Relation.new_instance(matthew_user.id, borrowing_item_relation.id, inst_1_id)
            matthew_bob_borrow_relation.write_to_db(self.mongo)
        else:
            matthew_bob_borrow_relation = matthew_bob_borrow_relation[0]

        bob_book_item.recalculate_implied_tags(self.mongo, True)

        # print("Search 'book, players: 4': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4")))
        # print("Search 'book, players: (4)': " + str(search_string_to_mongodb_query(self.mongo, "book, players: (4)")))
        # print("Search 'book, players: (4), test': " + str(search_string_to_mongodb_query(self.mongo, "book, players: (4), test")))
        # print("Search '(interesting), book, players: (4), test': " + str(search_string_to_mongodb_query(self.mongo, "(interesting), book, players: (4), test")))
        # print("Search '(help)': " + str(search_string_to_mongodb_query(self.mongo, "(help)")))
        # print("Search 'book, players - 4': " + str(search_string_to_mongodb_query(self.mongo, "book, players - 4")))
        # print("Search 'book, {players: (4)}': " + str(search_string_to_mongodb_query(self.mongo, "book, {players: (4)}")))
        # print("Search 'book, players: 4, -borrowed out': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out")))
        # print("Search 'book, players: 4 ::or -borrowed out': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4 ::or -borrowed out")))
        # print("Search 'book, (players: 4 ::or -borrowed out)': " + str(search_string_to_mongodb_query(self.mongo, "book, (players: 4 ::or -borrowed out)")))
        # print("Search 'book, players: 4, -borrowed out, ::name::contains::Bob': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, ::name::contains::Bob")))
        # print("Search 'book, players: 4, -borrowed out, ::has::author': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, ::has::author")))
        # print("Search 'book, players: 4, -borrowed out, -::has::author': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, -::has::author")))
        #
        # print("Search 'book, players: 4, -borrowed out, -::instance::damaged, ::has::author, ::name::contains::Bob': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, -::instance::damaged, ::has::author, ::name::contains::Bob")))
        # print("Search 'book, players: 4, -borrowed out, ::instance::damaged, ::has::author, ::name::contains::Bob': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, ::instance::damaged, ::has::author, ::name::contains::Bob")))
        # print("Search 'book, players: 4, -borrowed out, ::instance::uuid::equals::109358181, ::has::author, ::name::contains::Bob': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, ::instance::uuid::equals::109358181, ::has::author, ::name::contains::Bob")))
        # print("Search 'book, players: 4, -borrowed out, ::instance::uuid::equals::109358182, ::has::author, ::name::contains::Bob': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, ::instance::uuid::equals::109358182, ::has::author, ::name::contains::Bob")))
        # print("Search 'book, players: 4, -borrowed out, -::instance::uuid::equals::109358181, ::has::author, ::name::contains::Bob': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, -::instance::uuid::equals::109358181, ::has::author, ::name::contains::Bob")))
        #
        # print("Search 'book, players: 4, borrowed out, players: 3, players: 5': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, borrowed out, players: 3, players: 5")))
        # print("Search 'book, players: 4, -borrowed out, players: 3, players: 5': " + str(search_string_to_mongodb_query(self.mongo, "book, players: 4, -borrowed out, players: 3, players: 5")))
        # print("Search 'players: 3, -book, players: 4': " + str(search_string_to_mongodb_query(self.mongo, "players: 3, -book, players: 4")))
