# Captcha_bot
Captcha bot for telegram superchat
1) Run main.py

Unban is carried out by sending a message with the `/unban` command
(of course, if you know chat_id and user_id )

Changes:
1.Ban command was be added. You can type something like  /ban@botname user_id
and user no more send message in this chat.

2.If the user has not written messages for more than TIMEOUT_FOR_BAN,
then when he tries to write something to the chat, he is removed from the group
and sent to the black list.
