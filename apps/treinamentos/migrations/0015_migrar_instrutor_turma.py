from django.db import migrations


def forwards(apps, schema_editor):
    Instrutor = apps.get_model("treinamentos", "Instrutor")
    Turma = apps.get_model("treinamentos", "Turma")

    funcionario_field = None
    for field in Turma._meta.fields:
        if field.name == "instrutor":
            funcionario_field = field
            break

    if not funcionario_field:
        return

    funcionario_model = funcionario_field.remote_field.model

    instrutor_map = {}
    turmas = Turma.objects.exclude(instrutor_id=None).iterator()
    for turma in turmas:
        funcionario_id = turma.instrutor_id
        if not funcionario_id:
            continue
        funcionario = funcionario_model.objects.filter(pk=funcionario_id).first()
        if not funcionario:
            continue
        key = (funcionario.company_id, funcionario_id)
        instrutor_id = instrutor_map.get(key)
        if not instrutor_id:
            instrutor = Instrutor.objects.create(
                company_id=funcionario.company_id,
                nome=funcionario.nome,
                documento=getattr(funcionario, "cpf", "") or "",
                email=getattr(funcionario, "email", "") or "",
                telefone=getattr(funcionario, "telefone", "") or "",
                ativo=True,
            )
            instrutor_id = instrutor.pk
            instrutor_map[key] = instrutor_id
        turma.instrutor_novo_id = instrutor_id
        turma.save(update_fields=["instrutor_novo"])


def backwards(apps, schema_editor):
    # Nao e possivel reverter automaticamente (Instrutor pode nao ter equivalente em Funcionario).
    return


class Migration(migrations.Migration):

    dependencies = [
        ("treinamentos", "0014_instrutor"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name="turma",
            name="instrutor",
        ),
        migrations.RenameField(
            model_name="turma",
            old_name="instrutor_novo",
            new_name="instrutor",
        ),
    ]

