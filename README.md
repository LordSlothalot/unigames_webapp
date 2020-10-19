# Unigames Library Management System
[![License](https://img.shields.io/github/license/nonebot/nonebot.svg)](LICENSE)
[![](https://img.shields.io/badge/python-3.5%2B-blue.svg)]()
[![Framework](https://img.shields.io/badge/framework-Flask-orange.svg)]()\
The Unigames library management system is a website designed to keep track of all table-top games, gaming materials, and books held by the Unigames club.


# Installation

 1. Clone this repository
 2. Go to `backend` folder.
 3. Create a virtual environment and [install](https://github.com/LordSlothalot/unigames_webapp/tree/master/backend/README.md) all requirements.
 4. Install MongoDb (installation guide [here](https://docs.mongodb.com/manual/installation/#mongodb-community-edition-installation-tutorials)).
 5. Run `flask run`
 6. Go to [http://localhost:5000](http://localhost:5000/)

Upon deployment, MongoDB can also be connected remotely. You can hire an instance on [MongoDB Atlas]([https://www.mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)) and change the `app.config["MONGO_URI"]` variable to your instance's adress. 
 

## Features

The Unigames library management system consists of a public library and a management panel.
...
