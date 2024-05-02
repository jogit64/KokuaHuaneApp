from werkzeug.security import generate_password_hash

# Remplacez 'yourpassword' par le mot de passe que vous voulez hasher
hashed_password = generate_password_hash('yourpassword')
print(hashed_password)
