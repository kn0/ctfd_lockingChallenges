from CTFd.models import db, Challenges


class LockingChallenges(Challenges):
    """
    Model for the locking challenge type
    """
    __mapper_args__ = {'polymorphic_identity': 'locking'}
    id = db.Column(None, db.ForeignKey('challenges.id'), primary_key=True)
    unlock_at = db.Column(db.Integer)

    def __init__(self, name, description, value, category, type='locking', unlock_at=0):
        self.name = name
        self.description = description
        self.value = value
        self.category = category
        self.type = type
        self.unlock_at = unlock_at
