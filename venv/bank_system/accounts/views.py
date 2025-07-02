from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum
from io import BytesIO
import csv
from collections import defaultdict

from .forms import RegisterForm, LoginForm
from .models import BankAccount, Transaction, UserProfile

# PDF Generation (ReportLab & WeasyPrint)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.template.loader import render_to_string
from xhtml2pdf import pisa

# ---------------------- AUTH ------------------------

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # BankAccount will be created by signal automatically
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------------- DASHBOARD ------------------------

@login_required
def dashboard_view(request):
    account = BankAccount.objects.get(user=request.user)
    transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')[:5]

    deposits = Transaction.objects.filter(user=request.user, transaction_type='deposit').aggregate(Sum('amount'))['amount__sum'] or 0
    withdraws = Transaction.objects.filter(user=request.user, transaction_type='withdraw').aggregate(Sum('amount'))['amount__sum'] or 0

    profile_pic = None
    if hasattr(request.user, 'userprofile') and request.user.userprofile.image:
        profile_pic = request.user.userprofile.image.url

    return render(request, 'accounts/dashboard.html', {
        'account': account,
        'transactions': transactions,
        'deposits': float(deposits),
        'withdraws': float(withdraws),
        'profile_pic': profile_pic,
    })


# ---------------------- DEPOSIT / WITHDRAW ------------------------

@login_required
def deposit_withdraw_view(request):
    account = BankAccount.objects.get(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        amount = request.POST.get('amount')

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")

            if action == 'deposit':
                account.balance += amount
                Transaction.objects.create(user=request.user, transaction_type='deposit', amount=amount, description=f"Deposited Rs. {amount}")
                messages.success(request, f"Deposited Rs. {amount}")
            elif action == 'withdraw':
                if amount > account.balance:
                    messages.error(request, "Insufficient balance.")
                else:
                    account.balance -= amount
                    Transaction.objects.create(user=request.user, transaction_type='withdraw', amount=amount, description=f"Withdrawn Rs. {amount}")
                    messages.success(request, f"Withdrawn Rs. {amount}")
            account.save()

        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'accounts/deposit_withdraw.html', {'account': account})


# ---------------------- TRANSFER ------------------------

@login_required
def transfer_view(request):
    sender_account = BankAccount.objects.get(user=request.user)

    if request.method == 'POST':
        receiver_acc_no = request.POST.get('receiver_account')
        amount = request.POST.get('amount')

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            if receiver_acc_no == sender_account.account_number:
                raise ValueError("You cannot transfer to your own account.")

            receiver_account = BankAccount.objects.get(account_number=receiver_acc_no)
            if sender_account.balance < amount:
                raise ValueError("Insufficient balance.")

            sender_account.balance -= amount
            receiver_account.balance += amount
            sender_account.save()
            receiver_account.save()

            Transaction.objects.create(user=request.user, transaction_type='transfer', amount=amount, description=f"Transferred Rs. {amount} to account {receiver_acc_no}")
            Transaction.objects.create(user=receiver_account.user, transaction_type='deposit', amount=amount, description=f"Received Rs. {amount} from account {sender_account.account_number}")
            messages.success(request, f"Transferred Rs. {amount} to account {receiver_acc_no}")

        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'accounts/transfer.html', {'account': sender_account})


# ---------------------- TRANSACTION HISTORY ------------------------

@login_required
def transaction_history_view(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    txn_type = request.GET.get('type')

    if start_date:
        transactions = transactions.filter(timestamp__date__gte=start_date)
    if end_date:
        transactions = transactions.filter(timestamp__date__lte=end_date)
    if txn_type and txn_type != 'all':
        transactions = transactions.filter(transaction_type=txn_type)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Amount (Rs.)', 'Description'])
        for txn in transactions:
            writer.writerow([
                txn.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                txn.transaction_type.title(),
                txn.amount,
                txn.description
            ])
        return response

    return render(request, 'accounts/transactions.html', {
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
        'txn_type': txn_type,
    })


# ---------------------- EXPORT PDF VIEWS ------------------------

@login_required
def export_pdf_view(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('timestamp')

    monthly_data = defaultdict(list)
    for txn in transactions:
        month_key = txn.timestamp.strftime('%B %Y')
        monthly_data[month_key].append(txn)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(180, y, "📄 Monthly Transaction Report")
    y -= 30
    p.line(40, y, width - 40, y)
    y -= 30
    p.setFont("Helvetica", 11)

    for month, txns in monthly_data.items():
        if y < 100:
            p.showPage()
            y = height - 50

        p.setFont("Helvetica-Bold", 13)
        p.drawString(50, y, f"📅 {month}")
        y -= 20

        p.setFont("Helvetica-Bold", 11)
        p.setFillGray(0.9)
        p.rect(45, y - 15, width - 90, 18, fill=1, stroke=0)
        p.setFillGray(0.0)
        p.drawString(50, y - 12, "Date")
        p.drawString(150, y - 12, "Type")
        p.drawString(250, y - 12, "Amount (Rs.)")
        p.drawString(370, y - 12, "Description")
        y -= 25

        p.setFont("Helvetica", 10)
        for txn in txns:
            if y < 60:
                p.showPage()
                y = height - 50

            p.drawString(50, y, txn.timestamp.strftime('%d-%m-%Y'))
            p.drawString(150, y, txn.transaction_type.title())
            p.drawString(250, y, f"{txn.amount}")
            p.drawString(370, y, txn.description[:50])
            y -= 18

        y -= 15

    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


# ---------------------- HTML to PDF Receipt ------------------------

@login_required
def download_receipt_html_pdf(request, txn_id):
    txn = get_object_or_404(Transaction, id=txn_id, user=request.user)

    html_string = render_to_string('accounts/receipt_template.html', {
        'txn': txn,
        'user': request.user,
    })

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode('utf-8')), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{txn.id}.pdf"'
        return response
    else:
        return HttpResponse("Error generating PDF", status=500)


# ---------------------- PROFILE ------------------------

@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.save()

        if request.FILES.get('profile_image'):
            profile.image = request.FILES['profile_image']
            profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('profile')

    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'profile': profile,
    })


# ---------------------- HOME ------------------------

def home_view(request):
    return render(request, 'accounts/bankdash_home.html')
