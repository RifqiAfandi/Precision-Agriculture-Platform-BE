from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with sample users'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        
        # Clear existing users (optional - hati-hati di production!)
        if self.confirm_delete():
            User.objects.all().delete()
            self.stdout.write(self.style.WARNING('Deleted all existing users'))
        
        # Create sample users
        users_data = [
            {
                'email': 'admin@agriiweb.com',
                'name': 'Admin User',
                'company': 'Precision Agriculture',
                'password': 'admin123',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'demo@agriiweb.com',
                'name': 'Demo User',
                'company': 'Demo Company',
                'password': 'demo123',
            },
            {
                'email': 'user1@agriiweb.com',
                'name': 'John Doe',
                'company': 'AgriTech Solutions',
                'password': 'password123',
            },
            {
                'email': 'user2@agriiweb.com',
                'name': 'Jane Smith',
                'company': 'Smart Farming Co',
                'password': 'password123',
            },
            {
                'email': 'farmer@test.com',
                'name': 'Petani Sukses',
                'company': 'Kebun Makmur',
                'password': 'farmer123',
            },
        ]
        
        created_count = 0
        for user_data in users_data:
            is_staff = user_data.pop('is_staff', False)
            is_superuser = user_data.pop('is_superuser', False)
            
            if is_superuser:
                user = User.objects.create_superuser(**user_data)
                self.stdout.write(self.style.SUCCESS(f'✓ Created superuser: {user.email}'))
            else:
                user = User.objects.create_user(**user_data)
                if is_staff:
                    user.is_staff = True
                    user.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Created user: {user.email}'))
            
            created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully created {created_count} users'))
        self.stdout.write('\n📝 Login credentials:')
        for user_data in users_data:
            self.stdout.write(f"   Email: {user_data['email']} | Password: {user_data['password']}")
    
    def confirm_delete(self):
        """Ask user for confirmation before deleting existing data"""
        user_count = User.objects.count()
        if user_count == 0:
            return False
        
        answer = input(f'\n⚠️  There are {user_count} existing users. Delete them? (yes/no): ')
        return answer.lower() in ['yes', 'y']
