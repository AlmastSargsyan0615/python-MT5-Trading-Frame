
import smtplib
# creates SMTP session
s = smtplib.SMTP('smtp.gmail.com', 587)
# start TLS for security
s.starttls()
# Authentication
# s.login("jesspannhoff@gmail.com", "alwaysFriend.0514")
# # message to be sent
# message = "Message_you_need_to_send"
# # sending the mail
# s.sendmail("jesspannhoff@gmail.com", "vps.fortune.0802@outlook.com", message)
# # terminating the session
# s.quit()