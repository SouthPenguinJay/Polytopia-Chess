* [33m48b0212[m[33m ([m[1;31morigin/ValidateAllGetMoves[m[33m)[m Delete .suo
* [33mbeb1489[m Delete slnx.sqlite
* [33m31ef197[m Changed all get move functions so that they return valid moves only.  This mostly involved checking for on_board with new on_board function an checking for hypothetical_check.
* [33mbdf5f8d[m[33m ([m[1;31morigin/FixEnPassant[m[33m)[m Added EnPassant to pawn validate move, and added condition that pawn is in correct rank.
[31m|[m * [33m228f918[m[33m ([m[1;31morigin/ValidateKingCommits[m[33m)[m Delete slnx.sqlite
[31m|[m * [33mfeb453b[m Updated as per suggested changes
[31m|[m * [33m3a0188e[m Fixes to Validate King
[31m|[m[31m/[m  
*   [33m7870185[m[33m ([m[1;36mHEAD -> [m[1;32mmaster[m[33m, [m[1;31morigin/master[m[33m, [m[1;31morigin/HEAD[m[33m)[m Merge branch 'master' of https://github.com/SouthPenguinJay/Polytopia-Chess
[33m|[m[34m\[m  
[33m|[m *   [33mcb92fb7[m Merge pull request #17 from huntedhippo/patch-11
[33m|[m [35m|[m[36m\[m  
[33m|[m [35m|[m * [33m3e2050f[m Included suggested changes
[33m|[m [35m|[m * [33m4e76692[m Correct validate move final hypo check
[33m|[m * [36m|[m   [33m2bf2092[m Merge pull request #9 from huntedhippo/patch-3
[33m|[m [1;31m|[m[1;32m\[m [36m\[m  
[33m|[m [1;31m|[m * [36m|[m [33m71007e4[m Implemented suggested changes
[33m|[m [1;31m|[m * [36m|[m [33mad92105[m Change hypothetical_check
[33m|[m [1;31m|[m [36m|[m[36m/[m  
[33m|[m * [36m|[m   [33m16585e1[m Remove assertion in path_is_empty since it doesn't handle orthogonals anyway
[33m|[m [1;33m|[m[1;34m\[m [36m\[m  
[33m|[m [1;33m|[m * [36m|[m [33m5f38c1c[m Update as per convo
[33m|[m [1;33m|[m * [36m|[m [33m763d5d0[m Update chess.py
[33m|[m [1;33m|[m [36m|[m[36m/[m  
[33m|[m * [36m|[m   [33m3406584[m Merge pull request #14 from huntedhippo/patch-8
[33m|[m [1;35m|[m[1;36m\[m [36m\[m  
[33m|[m [1;35m|[m * [36m|[m [33mcfc3cf6[m Corrected rank file typo in get king moves castling
[33m|[m [1;35m|[m [36m|[m[36m/[m  
[33m|[m * [36m|[m   [33m7cc3d36[m Merge pull request #13 from huntedhippo/patch-7
[33m|[m [31m|[m[32m\[m [36m\[m  
[33m|[m [31m|[m * [36m|[m [33m719954b[m Correct typo in onboard section of validate move
[33m|[m [31m|[m [36m|[m[36m/[m  
[33m|[m * [36m|[m   [33md21b0ff[m Merge pull request #16 from huntedhippo/patch-10
[33m|[m [33m|[m[34m\[m [36m\[m  
[33m|[m [33m|[m * [36m|[m [33md448ff0[m Typo in 50 move game condition
[33m|[m [33m|[m [36m|[m[36m/[m  
[33m|[m * [36m|[m   [33m974c89f[m Merge pull request #11 from huntedhippo/patch-5
[33m|[m [35m|[m[36m\[m [36m\[m  
[33m|[m [35m|[m * [36m|[m [33m2b2c776[m Fix get pawn moves two in front
[33m|[m [35m|[m [36m|[m[36m/[m  
[33m|[m * [36m|[m   [33m3152d4f[m Merge pull request #7 from huntedhippo/patch-1
[33m|[m [36m|[m[1;32m\[m [36m\[m  
[33m|[m [36m|[m [1;32m|[m[36m/[m  
[33m|[m [36m|[m[36m/[m[1;32m|[m   
[33m|[m [36m|[m * [33m87792d7[m Update chess.py
[33m|[m [36m|[m[36m/[m  
[33m|[m * [33m1dedfd9[m Fix missing or mistyped names.
* [1;32m|[m [33m034b566[m Included suggested changes
* [1;32m|[m [33m44e5991[m Correct validate move final hypo check
* [1;32m|[m [33m2c596ab[m Implemented suggested changes
* [1;32m|[m [33m1931025[m Change hypothetical_check
* [1;32m|[m [33m073dce4[m Update as per convo
* [1;32m|[m [33m8f41458[m Update chess.py
* [1;32m|[m [33m4fec065[m Corrected rank file typo in get king moves castling
* [1;32m|[m [33ma0393e3[m Correct typo in onboard section of validate move
* [1;32m|[m [33m9ce5ef1[m Typo in 50 move game condition
* [1;32m|[m [33m9c49845[m Fix get pawn moves two in front
* [1;32m|[m [33m1bf2381[m Update chess.py
* [1;32m|[m [33m1b8182f[m[33m ([m[1;31morigin/add-rest-methods[m[33m)[m Order users by ELO.
* [1;32m|[m [33md8a461b[m Add methods for game-related endpoints.
* [1;32m|[m [33ma016a3c[m Add methods for account-related endpoints.
[1;32m|[m[1;32m/[m  
* [33m4d1dd2e[m Add basic flask setup.
* [33mfa57800[m Add email verification support to models.
* [33m5b730d3[m Don't load gamemodes and timers more than necessary.
*   [33m100d11f[m Merge pull request #6 from SouthPenguinJay/time-control
[1;33m|[m[1;34m\[m  
[1;33m|[m * [33m9a9b896[m Add a time control module.
[1;33m|[m[1;33m/[m  
* [33m541b58e[m Add threefold draw handling by storing every board position.
* [33m17ed556[m Switch ranks and files (oops) and combine checkmate/stalemate checking.
* [33m9eeb89c[m Add checks for checkmate and stalemate.
* [33m4834be1[m Check for moving into check.
* [33m0b121dc[m Validate chess moves.
*   [33mac61a0b[m Merge pull request #1 from SouthPenguinJay/add-models
[1;35m|[m[1;36m\[m  
[1;35m|[m * [33me89bec2[m Use constant time comparisons to avoid timing attacks, and sha3-256 rather than sha3-512.
[1;35m|[m * [33m560dde6[m Use pbkdf2_hmac for password hashing.
[1;35m|[m * [33m4a70a82[m Utility for incrementing turn, and set values with dynamic defaults at __init__ rather than with accessors.
[1;35m|[m * [33mf807f51[m Added start_game utility and turn counter.
[1;35m|[m * [33mff51f6a[m Split model string representations over multiple lines.
[1;35m|[m * [33mfd4a882[m Only store timers at the start of last turn to avoid constantly updating.
[1;35m|[m * [33mcaf8594[m Use interval fields to represent time.
[1;35m|[m * [33m192bb4a[m Add string representation to models.
[1;35m|[m * [33m2e7f4fd[m Gitignore pyc files.
[1;35m|[m * [33m1089afa[m Fix typo (BaseModel is defined locally, not by peewee).
[1;35m|[m * [33m42e7ab0[m Add representation for the board.
[1;35m|[m * [33m67acd2a[m Use enums for winner and conclusion type.
[1;35m|[m * [33m774473b[m Added models for users and games.
* [1;36m|[m [33mb0205b1[m Add flake8 config file.
[1;36m|[m[1;36m/[m  
* [33m09a4a59[m Added database and peewee setup.
* [33md0753db[m Initial commit
