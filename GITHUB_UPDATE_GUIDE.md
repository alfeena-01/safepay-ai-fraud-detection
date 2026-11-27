# Updating the existing SafePay GitHub repository safely

This ZIP contains source files, not the repository's `.git` history. Do not replace the online repository or push directly to `main`.

1. Clone your existing repository if you do not already have a local copy.
2. Open PowerShell in the cloned repository and update the integration branch:

```powershell
git checkout develop
git pull origin develop
git checkout -b feature/integration-hardening
```

3. Extract this ZIP into that cloned repository folder and allow the updated files to merge into the existing folder structure. Keep your `.git` folder untouched. Do not delete your own untracked files or any team member's work.
4. Review the changed files before staging:

```powershell
git status
git diff --stat
```

5. Run backend tests and frontend build using the commands in `README.md`.
6. Commit and push only the reviewed feature branch:

```powershell
git add .
git commit -m "Integrate SafePay auth, chatbot and investigation graph"
git push -u origin feature/integration-hardening
```

7. Open a Pull Request from `feature/integration-hardening` into `develop`. Ask the other three members to review shared API/schema/frontend files. Merge `develop` into `main` only after CI and team review pass.

Never commit `.env`, generated secrets, `backend/safepay.db`, private transaction files, `node_modules`, or virtual environments.
