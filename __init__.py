from flask import session, json
from CTFd.plugins.challenges import BaseChallenge, CHALLENGE_CLASSES
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.keys import get_key_class
from CTFd.models import db, Solves, WrongKeys, Keys, Files, Tags, Teams
from CTFd import utils
from .model import LockingChallenges


class CTFdLockingChallenge(BaseChallenge):
    id = "locking"  # Unique identifier used to register challenges
    name = "locking"  # Name of a challenge type
    templates = {  # Nunjucks templates used for each aspect of challenge editing & viewing
        'create': '/plugins/ctfd_lockingChallenges/assets/locking-challenge-create.njk',
        'update': '/plugins/ctfd_lockingChallenges/assets/locking-challenge-update.njk',
        'modal': '/plugins/ctfd_lockingChallenges/assets/locking-challenge-modal.njk',
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        'create': '/plugins/ctfd_lockingChallenges/assets/locking-challenge-create.js',
        'update': '/plugins/ctfd_lockingChallenges/assets/locking-challenge-update.js',
        'modal': '/plugins/ctfd_lockingChallenges/assets/locking-challenge-modal.js',
    }

    @staticmethod
    def create(request):
        """
        This method is used to process the challenge creation request.

        :param request:
        :return:
        """
        # Create challenge
        chal = LockingChallenges(
            name=request.form['name'],
            description=request.form['description'],
            value=request.form['value'],
            category=request.form['category'],
            type=request.form['chaltype'],
        )

        if 'hidden' in request.form:
            chal.hidden = True
        else:
            chal.hidden = False

        max_attempts = request.form.get('max_attempts')
        if max_attempts and max_attempts.isdigit():
            chal.max_attempts = int(max_attempts)

        unlock_at = request.form.get('unlock_at')
        if unlock_at and unlock_at.isdigit():
            chal.unlock_at = int(unlock_at)

        db.session.add(chal)
        db.session.commit()

        flag = Keys(chal.id, request.form['key'], request.form['key_type[0]'])
        if request.form.get('keydata'):
            flag.data = request.form.get('keydata')
        db.session.add(flag)

        db.session.commit()

        files = request.files.getlist('files[]')
        for f in files:
            utils.upload_file(file=f, chalid=chal.id)

        db.session.commit()

    @staticmethod
    def read(challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """

        data = {
            'id': challenge.id,
            'name': challenge.name,
            'value': challenge.value,
            'description': "This challenge has not been unlocked yet. You need at least {} points to play.".format(challenge.unlock_at),
            'category': challenge.category,
            'hidden': challenge.hidden,
            'max_attempts': challenge.max_attempts,
            'unlock_at': challenge.unlock_at,
            'locked':  True,
            'type': challenge.type,
            'type_data': {
                'id': CTFdLockingChallenge.id,
                'name': CTFdLockingChallenge.name,
                'templates': CTFdLockingChallenge.templates,
                'scripts': CTFdLockingChallenge.scripts,
            },
        }

        if session.get('admin') or not locked(challenge):
            data['locked'] = False
            data['description'] = str(challenge.description)

        return challenge, data

    @staticmethod
    def update(challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        challenge.name = request.form['name']
        challenge.description = request.form['description']
        challenge.value = int(request.form.get('value', 0)) if request.form.get('value', 0) else 0
        challenge.max_attempts = int(request.form.get('max_attempts', 0)) if request.form.get('max_attempts', 0) else 0
        challenge.unlock_at = int(request.form.get('unlock_at', 0)) if request.form.get('unlock_at', 0) else 0
        challenge.category = request.form['category']
        challenge.hidden = 'hidden' in request.form
        db.session.commit()
        db.session.close()

    @staticmethod
    def delete(challenge):
        """
        This method is used to delete the resources used by a challenge.

        :param challenge:
        :return:
        """
        WrongKeys.query.filter_by(chalid=challenge.id).delete()
        Solves.query.filter_by(chalid=challenge.id).delete()
        Keys.query.filter_by(chal=challenge.id).delete()
        files = Files.query.filter_by(chal=challenge.id).all()
        for f in files:
            utils.delete_file(f.id)
        Files.query.filter_by(chal=challenge.id).delete()
        Tags.query.filter_by(chal=challenge.id).delete()
        LockingChallenges.query.filter_by(id=challenge.id).delete()
        db.session.commit()

    @staticmethod
    def attempt(chal, request):
        """
        This method is used to check whether a given input is right or wrong. It does not make any changes and should
        return a boolean for correctness and a string to be shown to the user. It is also in charge of parsing the
        user's input from the request itself.

        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """
        team = Teams.query.filter_by(id=session['id']).first()
        if locked(chal):
          return False, 'Challenge Locked. You need at least {} points.'.format(chal.unlock_at)
 
        provided_key = request.form['key'].strip()
        chal_keys = Keys.query.filter_by(chal=chal.id).all()
        for chal_key in chal_keys:
            if get_key_class(chal_key.type).compare(chal_key.flag, provided_key):
                return True, 'Correct'
        return False, 'Incorrect'

    @staticmethod
    def solve(team, chal, request):
        """
        This method is used to insert Solves into the database in order to mark a challenge as solved.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        provided_key = request.form['key'].strip()
        solve = Solves(teamid=team.id, chalid=chal.id, ip=utils.get_ip(req=request), flag=provided_key)
        db.session.add(solve)
        db.session.commit()
        db.session.close()

    @staticmethod
    def fail(team, chal, request):
        """
        This method is used to insert WrongKeys into the database in order to mark an answer incorrect.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        provided_key = request.form['key'].strip()
        wrong = WrongKeys(teamid=team.id, chalid=chal.id, ip=utils.get_ip(request), flag=provided_key)
        db.session.add(wrong)
        db.session.commit()
        db.session.close()


def locked(challenge):
    """
    Tests if a challenge should be locked for the given user
    """
    
    if not challenge or challenge.type != 'locking':
        return False
    team = Teams.query.filter_by(id=session['id']).first()
    if not team:
        return True
    if team.score() >= challenge.unlock_at:
        return False
    return True


def chal_decorator(f):
    """
    Decorator that adds locked true/false data to output from /chals route
    """

    def chal_wrapper(*args, **kwargs):
        jresp = f()
        response = json.loads(jresp.data)
        for game in response['game']:
            if game['type'] != 'locking':
                game['locked'] = False
                continue
            challenge = LockingChallenges.query.filter_by(id=game['id']).first()
            if locked(challenge):           
                game['locked'] = True
            else:
                game['locked'] = False
        return json.jsonify(response)

    return chal_wrapper


def load(app):
    # Create new locking_challenge table if necessary
    app.db.create_all()
    # Register new challenge type
    CHALLENGE_CLASSES["locking"] = CTFdLockingChallenge
    # Register plugin assets
    register_plugin_assets_directory(app, base_path='/plugins/ctfd_lockingChallenges/assets/')
    # Decorate /chals route
    app.view_functions['challenges.chals'] = chal_decorator(app.view_functions['challenges.chals'])
