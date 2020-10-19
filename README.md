# Unigames Library Management System
[![License](https://img.shields.io/github/license/nonebot/nonebot.svg)](LICENSE)
[![](https://img.shields.io/badge/python-3.5%2B-blue.svg)]()
[![Framework](https://img.shields.io/badge/framework-Flask-orange.svg)]()\
The Unigames library management system is a website designed to keep track of all table-top games, gaming materials, and books held by the Unigames club.


# Installation

 1. Clone this repository
 2. Go to `backend` folder.
 3. Create a virtual environment and [install](https://github.com/LordSlothalot/unigames_webapp/tree/master/backend/README.md) all requirements.
 4. Install MongoDb (installation guide [here](https://docs.mongodb.com/manual/installation/#mongodb-community-edition-installation-tutorials).
 5. Run `flask run`
 6. Go to [http://localhost:5000](http://localhost:5000/)

Upon deployment, MongoDB can also be connected remotely. You can hire an instance on [MongoDB Atlas]([https://www.mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)) and change the `app.config["MONGO_URI"]` variable to your instance's adress. 
 

## Features

The Unigames library management system consists of a public library and a management panel.
**Features include:**
 - Add/Edit/Delete library items, users, and tags.
 - Editable access control for different member groups.
 - Fast search & Syntactic query for items.
 - Implicative tagging system to improve searching.
 - Upload/Delete item cover image.
 - Enhanced UI. 

## Website UI

 - Public library UI
<a href="https://ibb.co/GnDkc0z"><img src="https://i.ibb.co/n6yfzbx/Wechat-IMG1.jpg" alt="Wechat-IMG1" border="0"></a>

 - Managerial panel UI.
<a href="https://ibb.co/55RrgG0"><img src="https://i.ibb.co/qRrN37S/Wechat-IMG2.jpg" alt="Wechat-IMG2" border="0"></a>
> **Bootstrap4** and an open source theme **SB Admin2** are used to enhance the visual design.

## About

The Unigames Library Management System is written by Group32 of CITS3200 unit. Group members include Matthew Chidlow, Luke Stagoll, Paris Loney, Mingchuan Tian, and Sirui Wang.

