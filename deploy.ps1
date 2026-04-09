# Initialize git if not already
if (!(Test-Path .git)) {
    git init
}

# Add all files
git add .
git commit -m "Initial commit: TeachMe platform setup"

# Set up remotes
# Note: You must update these handles if you change your repository names.
git remote add origin https://github.com/hengds2f/teachme.git
git remote add huggingface https://huggingface.co/spaces/hengds2f/teachme

Write-Host "Pushing to GitHub..."
git push -u origin master --force

Write-Host "Pushing to Hugging Face Spaces..."
git push -u huggingface master --force

Write-Host "Deployment completed. Please ensure you have added the GEMINI_API_KEY to your HuggingFace Space secrets."
