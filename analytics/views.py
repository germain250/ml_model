from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import School, Profile, Student, Threshold
from .services import predict_analysis
import json

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.profile.role == 'SUPER_ADMIN':
                return redirect('super_admin_overview')
            return redirect('dos_overview')
    else:
        form = AuthenticationForm()
    return render(request, 'analytics/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def super_admin_overview(request):
    if request.user.profile.role != 'SUPER_ADMIN':
        return redirect('dos_overview')
    schools = School.objects.all()
    total_students = Student.objects.count()
    total_dos = User.objects.filter(profile__role='DOS').count()
    return render(request, 'analytics/admin_overview.html', {
        'schools': schools,
        'total_students': total_students,
        'total_dos': total_dos,
    })

@login_required
def super_admin_schools(request):
    if request.user.profile.role != 'SUPER_ADMIN':
        return redirect('dos_overview')
    schools = School.objects.all().order_by('-created_at')
    return render(request, 'analytics/admin_schools.html', {'schools': schools})

@login_required
def super_admin_add_school(request):
    if request.user.profile.role != 'SUPER_ADMIN':
        return redirect('dos_overview')
    error = None
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        dos_username = request.POST.get('dos_username')
        dos_password = request.POST.get('dos_password')
        if User.objects.filter(username=dos_username).exists():
            error = f'The username "{dos_username}" is already taken. Please choose another.'
        else:
            school = School.objects.create(name=name, address=address)
            Threshold.objects.create(school=school, pass_mark=50.0)
            dos_user = User.objects.create_user(username=dos_username, password=dos_password)
            dos_user.profile.role = 'DOS'
            dos_user.profile.school = school
            dos_user.profile.save()
            return redirect('super_admin_schools')
    return render(request, 'analytics/admin_add_school.html', {'error': error})

# Keep old URL working (redirect)
@login_required
def super_admin_dashboard(request):
    return redirect('super_admin_overview')

@login_required
def dos_dashboard(request):
    if request.user.profile.role != 'DOS':
        return redirect('super_admin_dashboard')
    
    school = request.user.profile.school
    if not school:
        return render(request, 'analytics/dos_dashboard.html', {'error': 'No school assigned to your profile.'})
    
    students = Student.objects.filter(school=school).order_by('-created_at')
    threshold, created = Threshold.objects.get_or_create(school=school)
    
    if request.method == 'POST' and 'set_threshold' in request.POST:
        threshold.pass_mark = float(request.POST.get('pass_mark', 50.0))
        threshold.save()
        return redirect('dos_overview')
        
    return render(request, 'analytics/dos_dashboard.html', {
        'students': students,
        'threshold': threshold,
        'school': school,
        'profile': request.user.profile
    })

@login_required
def dos_overview(request):
    if request.user.profile.role != 'DOS':
        return redirect('super_admin_overview')
    school = request.user.profile.school
    if not school:
        return render(request, 'analytics/dos_overview.html', {'error': 'No school has been assigned to your account.'})
    students = Student.objects.filter(school=school)
    threshold, _ = Threshold.objects.get_or_create(school=school)
    if request.method == 'POST' and 'set_threshold' in request.POST:
        threshold.pass_mark = float(request.POST.get('pass_mark', 50.0))
        threshold.save()
        return redirect('dos_overview')
    passing = sum(1 for s in students if s.previous_scores >= threshold.pass_mark)
    pass_rate = round((passing / students.count() * 100), 1) if students.count() > 0 else 0
    return render(request, 'analytics/dos_overview.html', {
        'school': school,
        'threshold': threshold,
        'student_count': students.count(),
        'pass_rate': pass_rate,
        'passing': passing,
    })

@login_required
def dos_students(request):
    if request.user.profile.role != 'DOS':
        return redirect('super_admin_overview')
    school = request.user.profile.school
    students = Student.objects.filter(school=school).order_by('-created_at')
    threshold, _ = Threshold.objects.get_or_create(school=school)
    return render(request, 'analytics/dos_students.html', {
        'students': students,
        'school': school,
        'threshold': threshold,
    })

@login_required
def dos_add_student(request):
    if request.user.profile.role != 'DOS':
        return redirect('super_admin_overview')
    school = request.user.profile.school
    error = None
    if request.method == 'POST':
        try:
            P = request.POST.get
            student = Student.objects.create(
                name=P('name'),
                school=school,
                hours_studied=int(P('Hours_Studied', 20)),
                attendance=int(P('Attendance', 90)),
                sleep_hours=int(P('Sleep_Hours', 7)),
                previous_scores=int(P('Previous_Scores', 70)),
                tutoring_sessions=int(P('Tutoring_Sessions', 0)),
                physical_activity=int(P('Physical_Activity', 3)),
                parental_involvement=P('Parental_Involvement', 'Medium'),
                access_to_resources=P('Access_to_Resources', 'Medium'),
                extracurricular_activities=P('Extracurricular_Activities', 'No'),
                motivation_level=P('Motivation_Level', 'Medium'),
                internet_access=P('Internet_Access', 'Yes'),
                family_income=P('Family_Income', 'Medium'),
                teacher_quality=P('Teacher_Quality', 'Medium'),
                school_type=P('School_Type', 'Public'),
                peer_influence=P('Peer_Influence', 'Neutral'),
                learning_disabilities=P('Learning_Disabilities', 'No'),
                parental_education_level=P('Parental_Education_Level', 'College'),
                distance_from_home=P('Distance_from_Home', 'Near'),
                gender=P('Gender', 'Male')
            )
            return redirect('dos_students')
        except Exception as e:
            error = str(e)
    return render(request, 'analytics/dos_add_student.html', {'school': school, 'error': error})

@login_required
def dos_settings(request):
    if request.user.profile.role != 'DOS':
        return redirect('super_admin_overview')
    school = request.user.profile.school
    threshold, _ = Threshold.objects.get_or_create(school=school)
    success = None
    error = None
    if request.method == 'POST':
        if 'set_threshold' in request.POST:
            try:
                threshold.pass_mark = float(request.POST.get('pass_mark', 50.0))
                threshold.save()
                
                # Kick off background retrain of ML models
                from analytics.services import trigger_retrain
                trigger_retrain(threshold.pass_mark)
                
                success = 'Pass mark updated successfully. The AI model is being retrained in the background.'
            except Exception as e:
                error = str(e)
        elif 'change_password' in request.POST:
            new_pw = request.POST.get('new_password')
            confirm_pw = request.POST.get('confirm_password')
            if new_pw != confirm_pw:
                error = 'Passwords do not match.'
            else:
                request.user.set_password(new_pw)
                request.user.save()
                login(request, request.user)
                success = 'Password changed successfully.'
    return render(request, 'analytics/dos_settings.html', {
        'school': school,
        'threshold': threshold,
        'success': success,
        'error': error,
    })

@login_required
def api_change_password(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        new_password = request.POST.get('new_password')
        user = request.user
        user.set_password(new_password)
        user.save()
        
        # Update profile to indicate first login is complete
        profile = user.profile
        profile.is_first_login = False
        profile.save()
        
        # We need to re-authenticate the user as set_password logs them out in some versions/configs
        login(request, user)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def api_add_student(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        P = request.POST.get
        student = Student.objects.create(
            name=P('name'),
            school=request.user.profile.school,
            hours_studied=int(P('Hours_Studied', 20)),
            attendance=int(P('Attendance', 90)),
            sleep_hours=int(P('Sleep_Hours', 7)),
            previous_scores=int(P('Previous_Scores', 70)),
            tutoring_sessions=int(P('Tutoring_Sessions', 0)),
            physical_activity=int(P('Physical_Activity', 3)),
            parental_involvement=P('Parental_Involvement', 'Medium'),
            access_to_resources=P('Access_to_Resources', 'Medium'),
            extracurricular_activities=P('Extracurricular_Activities', 'No'),
            motivation_level=P('Motivation_Level', 'Medium'),
            internet_access=P('Internet_Access', 'Yes'),
            family_income=P('Family_Income', 'Medium'),
            teacher_quality=P('Teacher_Quality', 'Medium'),
            school_type=P('School_Type', 'Public'),
            peer_influence=P('Peer_Influence', 'Neutral'),
            learning_disabilities=P('Learning_Disabilities', 'No'),
            parental_education_level=P('Parental_Education_Level', 'College'),
            distance_from_home=P('Distance_from_Home', 'Near'),
            gender=P('Gender', 'Male')
        )
        
        threshold = Threshold.objects.get(school=student.school)
        student_data = {
            'Hours_Studied': student.hours_studied,
            'Attendance': student.attendance,
            'Sleep_Hours': student.sleep_hours,
            'Previous_Scores': student.previous_scores,
            'Tutoring_Sessions': student.tutoring_sessions,
            'Physical_Activity': student.physical_activity,
            'Parental_Involvement': student.parental_involvement,
            'Access_to_Resources': student.access_to_resources,
            'Extracurricular_Activities': student.extracurricular_activities,
            'Motivation_Level': student.motivation_level,
            'Internet_Access': student.internet_access,
            'Family_Income': student.family_income,
            'Teacher_Quality': student.teacher_quality,
            'School_Type': student.school_type,
            'Peer_Influence': student.peer_influence,
            'Learning_Disabilities': student.learning_disabilities,
            'Parental_Education_Level': student.parental_education_level,
            'Distance_from_Home': student.distance_from_home,
            'Gender': student.gender
        }
        
        results = predict_analysis(student_data, threshold=threshold.pass_mark)
        results['student_id'] = student.id
        results['student_name'] = student.name
        
        return JsonResponse(results)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def api_edit_student(request, student_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        student = get_object_or_404(Student, id=student_id, school=request.user.profile.school)
        P = request.POST.get
        
        student.name = P('name', student.name)
        student.hours_studied = int(P('Hours_Studied', student.hours_studied))
        student.attendance = int(P('Attendance', student.attendance))
        student.sleep_hours = int(P('Sleep_Hours', student.sleep_hours))
        student.previous_scores = int(P('Previous_Scores', student.previous_scores))
        student.tutoring_sessions = int(P('Tutoring_Sessions', student.tutoring_sessions))
        student.physical_activity = int(P('Physical_Activity', student.physical_activity))
        
        # Optional features
        student.parental_involvement = P('Parental_Involvement', student.parental_involvement)
        student.access_to_resources = P('Access_to_Resources', student.access_to_resources)
        student.extracurricular_activities = P('Extracurricular_Activities', student.extracurricular_activities)
        student.motivation_level = P('Motivation_Level', student.motivation_level)
        student.internet_access = P('Internet_Access', student.internet_access)
        student.family_income = P('Family_Income', student.family_income)
        student.teacher_quality = P('Teacher_Quality', student.teacher_quality)
        student.school_type = P('School_Type', student.school_type)
        student.peer_influence = P('Peer_Influence', student.peer_influence)
        student.learning_disabilities = P('Learning_Disabilities', student.learning_disabilities)
        student.parental_education_level = P('Parental_Education_Level', student.parental_education_level)
        student.distance_from_home = P('Distance_from_Home', student.distance_from_home)
        student.gender = P('Gender', student.gender)
        
        student.save()
        
        threshold = Threshold.objects.get(school=student.school)
        student_data = {
            'Hours_Studied': student.hours_studied,
            'Attendance': student.attendance,
            'Sleep_Hours': student.sleep_hours,
            'Previous_Scores': student.previous_scores,
            'Tutoring_Sessions': student.tutoring_sessions,
            'Physical_Activity': student.physical_activity,
            'Parental_Involvement': student.parental_involvement,
            'Access_to_Resources': student.access_to_resources,
            'Extracurricular_Activities': student.extracurricular_activities,
            'Motivation_Level': student.motivation_level,
            'Internet_Access': student.internet_access,
            'Family_Income': student.family_income,
            'Teacher_Quality': student.teacher_quality,
            'School_Type': student.school_type,
            'Peer_Influence': student.peer_influence,
            'Learning_Disabilities': student.learning_disabilities,
            'Parental_Education_Level': student.parental_education_level,
            'Distance_from_Home': student.distance_from_home,
            'Gender': student.gender
        }
        
        results = predict_analysis(student_data, threshold=threshold.pass_mark)
        results['student_id'] = student.id
        results['student_name'] = student.name
        
        return JsonResponse(results)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def api_delete_student(request, student_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        student = get_object_or_404(Student, id=student_id, school=request.user.profile.school)
        student.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def student_deliberate(request, student_id):
    student = get_object_or_404(Student, id=student_id, school=request.user.profile.school)
    threshold = Threshold.objects.get(school=student.school)
    
    student_data = {
        'Hours_Studied': student.hours_studied,
        'Attendance': student.attendance,
        'Sleep_Hours': student.sleep_hours,
        'Previous_Scores': student.previous_scores,
        'Tutoring_Sessions': student.tutoring_sessions,
        'Physical_Activity': student.physical_activity,
        'Parental_Involvement': student.parental_involvement,
        'Access_to_Resources': student.access_to_resources,
        'Extracurricular_Activities': student.extracurricular_activities,
        'Motivation_Level': student.motivation_level,
        'Internet_Access': student.internet_access,
        'Family_Income': student.family_income,
        'Teacher_Quality': student.teacher_quality,
        'School_Type': student.school_type,
        'Peer_Influence': student.peer_influence,
        'Learning_Disabilities': student.learning_disabilities,
        'Parental_Education_Level': student.parental_education_level,
        'Distance_from_Home': student.distance_from_home,
        'Gender': student.gender
    }
    
    results = predict_analysis(student_data, threshold=threshold.pass_mark)
    
    # Mock some historical data for "past graphs"
    # In a real app, this would be fetched from a history table
    history_data = [
        {'date': 'Jan', 'score': student.previous_scores - 5},
        {'date': 'Feb', 'score': student.previous_scores - 2},
        {'date': 'Mar', 'score': student.previous_scores},
        {'date': 'Apr', 'score': results['score']}
    ]
    
    context = {
        'student': student,
        'results': results,
        'history_json': history_data,
        'threshold': threshold
    }
    return render(request, 'analytics/student_deliberate.html', context)

def dashboard(request):
    return redirect('login')
