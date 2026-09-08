# GitHub protection setup for ActiLab

The files in this repository support a maintainer-reviewed contribution model, but GitHub access control itself is configured in the repository settings.

Recommended configuration for the default branch (`main`):

1. Open **Repository → Settings → Rules → Rulesets → New branch ruleset**.
2. Name it `Protect ActiLab main` and set enforcement to **Active**.
3. Target the **default branch**.
4. Configure the bypass list so only the primary maintainer/repository administrator can bypass the rules when necessary.
5. Enable **Restrict updates** so only bypass actors can update the protected branch directly.
6. Enable **Restrict deletions** and **Block force pushes**.
7. Enable **Require a pull request before merging**.
8. Require at least **1 approving review**.
9. Enable **Require review from Code Owners** so `.github/CODEOWNERS` makes `@mayank-ramchandani` approval mandatory.
10. Optionally require automated status checks once CI tests are configured.

For a public personal repository, people who are not collaborators cannot push to your repository by default; they can fork it and submit pull requests. Avoid granting collaborator/write access unless someone genuinely needs it. For a private repository owned by a personal account, GitHub personal repositories do not provide a read-only collaborator role; use an organization if you need private read-only access with more granular permissions.
