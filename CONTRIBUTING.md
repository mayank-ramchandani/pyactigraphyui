# Contributing to ActiLab

ActiLab welcomes suggestions, bug reports, and proposed improvements while keeping the production code under maintainer control.

## Preferred contribution workflow

1. Open a GitHub Issue for a bug or feature suggestion, or fork the repository.
2. Make proposed code changes in your own fork/branch.
3. Open a Pull Request against the protected default branch.
4. The ActiLab maintainer reviews the proposal and decides whether it should be accepted, revised, or declined.
5. Only an approved merge into the protected branch can become part of the main ActiLab codebase/deployment.

Do not commit participant data, credentials, access tokens, private URLs, or other sensitive information.

## Repository protection

The repository should use a GitHub branch ruleset for the default branch that blocks direct updates by other users and requires a pull request plus Code Owner approval. The repository includes `.github/CODEOWNERS` assigning all paths to `@mayank-ramchandani`; GitHub protection settings must also be enabled for that file to be enforced.
