import sqlalchemy as sq
# модель специальный класс для работы с таблицами
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

# создание классов для работы с таблицами sql
class User(Base):
    __tablename__ = 'user'

    id = sq.Column(sq.Integer, primary_key=True)
    chat_id = sq.Column(sq.BigInteger, unique=True)


class EnglWordUser(Base):
    __tablename__ = 'user_word'

    id = sq.Column(sq.Integer, primary_key=True)
    russian_word = sq.Column(sq.String(length=40), unique=True)
    target_word = sq.Column(sq.String(length=40), unique=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('user.id'), nullable=False)

    user = relationship(User, backref='word')

class EnglWord(Base):
    __tablename__ = 'word'

    id = sq.Column(sq.Integer, primary_key=True)
    russian_word = sq.Column(sq.String(length=40), unique=True)
    target_word = sq.Column(sq.String(length=40), unique=True)

    def __str__(self):
        return f'{self.id}: {self.russian_word} - {self.target_word}'