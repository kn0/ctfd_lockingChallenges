CTFd_LockingChallenges
======================
This [CTFd](https://ctfd.io/) plugin provides a "locking" challenge type which prevents teams from viewing challenges until they have the necessary points required by the challenge. By locking challenges, it is possible to force teams to attempt challenges across different categories and encourage collaboration.

## Install
Clone this repository into the CTFd plugins folder

## Notes
* Teams can still access uploaded files, even on locked challenges. As a workaround, use 7z or similar to encrypt the challenge file, and include the passphrase in the challenge text.
* The challenge info for a locked challenge includes a 'locked' boolean value. By updating your theme's `chalboard.js` it is possible to add custom CSS to change the way locked challenges appear. For example:

```py
if (chalinfo.locked){
  var chalbutton = $("<button class='btn btn-dark challenge-button locked-challenge w-100 text-truncate pt-3 pb-3 mb-2' value='{0}'><i class='fas fa-lock corner-button-check'></i></button>".format(chalinfo.id));
```

