# Vercel Deployment Guide for WAFUNGI-NATION

This guide explains how to deploy your Django application to Vercel with Neon PostgreSQL database.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Neon Database**: You already have a Neon PostgreSQL database set up
3. **Vercel CLI** (optional): Install with `npm i -g vercel`

## Configuration Files Already Set Up

The following files have been configured for Vercel deployment:

- `vercel.json` - Vercel configuration for Django
- `wafungi_nation/settings.py` - Updated for PostgreSQL and WhiteNoise
- `.env` - Environment variables (do not commit this file!)
- `requirements.txt` - Python dependencies

## Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Vercel deployment"
   git push origin main
   ```

2. **Import project to Vercel**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Import your GitHub repository
   - Click "Import Project"

3. **Configure Environment Variables**
   In the Vercel dashboard, go to Settings > Environment Variables and add:

   ```
   DATABASE_URL=postgresql://neondb_owner:npg_FzBU70ObAnwS@ep-orange-queen-anmwi0k8-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require
   DEBUG=False
   SECRET_KEY=your-production-secret-key-here
   ALLOWED_HOSTS=.vercel.app,yourdomain.com
   MPESA_ENVIRONMENT=sandbox
   MPESA_CONSUMER_KEY=your_sandbox_key
   MPESA_CONSUMER_SECRET=your_sandbox_secret
   MPESA_BUSINESS_SHORT_CODE=174379
   MPESA_PASSKEY=your_sandbox_passkey
   PAYMENT_GATEWAY_API_KEY=your-payment-gateway-key
   ```

   > **Important**: Generate a new SECRET_KEY for production! Use:
   > ```python
   > from django.core.management.utils import get_random_secret_key
   > print(get_random_secret_key())
   > ```

4. **Deploy**
   - Click "Deploy"
   - Vercel will build and deploy your application

### Option 2: Deploy via Vercel CLI

1. **Login to Vercel**
   ```bash
   vercel login
   ```

2. **Deploy**
   ```bash
   vercel
   ```

3. **Set environment variables**
   ```bash
   vercel env add DATABASE_URL production
   vercel env add DEBUG False production
   vercel env add SECRET_KEY your-production-secret-key-here production
   # Add other environment variables as needed
   ```

4. **Deploy to production**
   ```bash
   vercel --prod
   ```

## Post-Deployment Tasks

### 1. Run Migrations

After deployment, you need to run migrations. Vercel serverless functions don't persist, so you'll need to run migrations manually or set up a migration script.

**Option A: Run migrations locally pointing to production database**

```bash
# Set the DATABASE_URL to your production Neon database
set DATABASE_URL=postgresql://neondb_owner:npg_FzBU70ObAnwS@ep-orange-queen-anmwi0k8-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require
python manage.py migrate
```

**Option B: Use Vercel's build hooks**

You can modify `vercel.json` to run migrations during build:

```json
{
  "buildCommand": "python manage.py collectstatic --noinput && python manage.py migrate"
}
```

### 2. Create Superuser

```bash
set DATABASE_URL=postgresql://neondb_owner:npg_FzBU70ObAnwS@ep-orange-queen-anmwi0k8-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require
python manage.py createsuperuser
```

### 3. Configure M-Pesa Callback URL

Update the `MPESA_CALLBACK_URL` in your settings or environment variables to point to your Vercel deployment URL:

```
MPESA_CALLBACK_URL=https://your-project.vercel.app/mpesa/callback/
```

## Important Notes

### Static Files
- WhiteNoise is configured to serve static files
- Run `python manage.py collectstatic` before deployment (Vercel does this automatically)
- Static files will be served from `/static/` URL

### Media Files
- Media files (user uploads) are stored locally in the `/media/` directory
- For production, consider using a cloud storage service like AWS S3 or Cloudinary
- Vercel's serverless functions have limited storage

### Database
- The app is configured to use Neon PostgreSQL in production
- Connection pooling is enabled with `conn_max_age=600`
- SSL is required for the database connection

### Environment Variables
- Never commit `.env` file to version control
- All sensitive data should be stored as environment variables in Vercel
- Local development can use the `.env` file

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Make sure all dependencies are in `requirements.txt`
   - Run `pip freeze > requirements.txt` to update

2. **Database connection errors**
   - Verify `DATABASE_URL` is correct
   - Check that your Neon database allows connections from Vercel IPs

3. **Static files not loading**
   - Run `python manage.py collectstatic --noinput`
   - Check that WhiteNoise middleware is in place

4. **500 Internal Server Error**
   - Check Vercel function logs in the dashboard
   - Set `DEBUG=True` temporarily to see detailed errors

### Viewing Logs

In the Vercel dashboard:
1. Go to your project
2. Click on "Functions" tab
3. Select the function and view logs

Or use CLI:
```bash
vercel logs your-project.vercel.app
```

## Updating Your Deployment

After making changes:

```bash
git add .
git commit -m "Your changes"
git push origin main
```

Vercel will automatically deploy the changes if you have GitHub integration enabled.

## Security Recommendations

1. **Use a strong SECRET_KEY** - Generate a new one for production
2. **Keep DEBUG=False** in production
3. **Use environment variables** for all sensitive data
4. **Enable HTTPS** (Vercel does this automatically)
5. **Set up proper CORS** if you have API endpoints
6. **Use a production email service** for sending emails

## Additional Resources

- [Vercel Python Runtime](https://vercel.com/docs/runtimes#official-runtimes/python)
- [Django on Vercel](https://vercel.com/guides/deploying-django-with-vercel)
- [Neon PostgreSQL Documentation](https://neon.tech/docs)
- [WhiteNoise Documentation](https://whitenoise.readthedocs.io/)