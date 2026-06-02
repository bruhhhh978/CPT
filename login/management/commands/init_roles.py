from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from login.models import UserProfile

class Command(BaseCommand):
    help = 'Initialize user profiles for existing users without profiles'

    def handle(self, *args, **options):
        # Get all users without profiles
        users_without_profile = []
        for user in User.objects.all():
            try:
                user.profile
            except UserProfile.DoesNotExist:
                users_without_profile.append(user)
        
        # Create profiles for users without them
        for user in users_without_profile:
            if user.is_superuser:
                role = 'manager'
            elif user.is_staff:
                role = 'user'
            else:
                role = 'user'
            
            UserProfile.objects.create(user=user, role=role)
            self.stdout.write(f'Created profile for {user.username} with role: {role}')
        
        if users_without_profile:
            self.stdout.write(self.style.SUCCESS(f'Successfully created {len(users_without_profile)} user profiles'))
        else:
            self.stdout.write(self.style.WARNING('All users already have profiles'))
