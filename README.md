# Polytopia-Chess
A chess game with custom pieces and boards. Join the discord https://discord.gg/55NwUbD

## Setting up the server

  1. Install Postgres, if you haven't already
  2. Create a new Postgres role, eg. `polychess`.
  3. Create a database for the role, eg. `polychess`.
  4. Make a file called `server/config.json`, like so:
     ```json
     {
         "db_name": "polychess",
         "db_user": "polychess",
         "db_password": "******"
     }
     ```
  5. \<insert instructions for running the actual server, once that is set up\>
  6. Have fun!
