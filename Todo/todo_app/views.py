from django.shortcuts import render, redirect
from .models import todo
from .forms import *

# Create your views here.

def index(request):
    todo_list = todo.objects.all()
    form = TodoForm()
    if request.method == 'POST':
        form = TodoForm(request.POST)
        if form.is_valid():
            form.save()
        return redirect('/')

    context= {'todo_list':todo_list, 'form':form}
    return render(request,"index.html", context)

def updateTodo(request, pk):
    task =todo.objects.get(id=pk)
    form = TodoForm(instance=task)
    if request.method == 'POST':
        form = TodoForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('/')

    context= {'form':form}
    return render(request, 'updates.html',context)

def deleteTodo(request, pk):
    task = todo.objects.get(id=pk)

    if request.method== "POST":
        task.delete()
        return redirect('/')
    context= {'task':task}
    return render(request,'delete.html',context)



