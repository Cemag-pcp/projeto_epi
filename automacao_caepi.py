import argparse
import csv
import ftplib
import io
import os
import re
import zipfile

import pandas as pd

class BaseDadosCaEPI:
    baseDadosDF = None 
    nomeArquivoBase = 'tgg_export_caepi.txt'
    nomeArquivoConfigNomesColunas = 'config_nomes_colunas.csv'
    nomeArquivoCSV = 'tgg_export_caepi.csv'
    nomeArquivoErros = 'CAs_com_erros.txt'    
    urlBase = 'ftp.mtps.gov.br'
    caminho = 'portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/'
    nColunas = 19


    nomeColunas = [
        "RegistroCA",
        "DataValidade",
        "Situacao",
        "NRProcesso",
        "CNPJ",
        "RazaoSocial",
        "Natureza",
        "NomeEquipamento",
        "DescricaoEquipamento",
        "MarcaCA",
        "Referencia",
        "Cor",
        "AprovadoParaLaudo",
        "RestricaoLaudo",
        "ObservacaoAnaliseLaudo",
        "CNPJLaboratorio",
        "RazaoSocialLaboratorio",
        "NRLaudo",
        "Norma"        
    ]

    def __init__(self):
        self = self

    def _baixarArquivoBaseCaEPI(self):
        if os.path.exists(self.nomeArquivoBase):
            os.remove(self.nomeArquivoBase)

        ftp = ftplib.FTP(self.urlBase)
        ftp.login()
        ftp.cwd(self.caminho)

        nomeArquivoZip = 'tgg_export_caepi.zip'
        r = io.BytesIO()

        ftp.retrbinary(f'RETR {nomeArquivoZip}', r.write)

        arquivoZip = zipfile.ZipFile(r)

        arquivoZip.extractall()
    
    def _transformarEmDataFrame(self):          
        listaCas = self._retornarCAsSemErros()
        cols = listaCas[0]
        self.baseDadosDF = pd.DataFrame(listaCas, columns=cols)        

        self.baseDadosDF.columns = self.__retornaNomesColunas()
        self._salvar_csv()

    def _salvar_csv(self) -> None:
        if self.baseDadosDF is None:
            return
        self.baseDadosDF.to_csv(self.nomeArquivoCSV, index=False, encoding="utf-8")

    def __retornaNomesColunas(self):
        arquivo = open(self.nomeArquivoConfigNomesColunas, encoding='UTF-8')

        return arquivo.readline().split(',')

    def _retornarCAsSemErros(self) -> list:
        listaCAsValidos = []
        listaCAsInvalidos = []

        with open(self.nomeArquivoBase, encoding='UTF-8') as arquivo:
            reader = csv.reader(arquivo, delimiter='|', quotechar='"')
            
            for linhaDf in reader:
                if len(linhaDf) > self.nColunas:
                    # Reconstrói a linha original para tratamento
                    linha_original = '|'.join(linhaDf)
                    resul_tratamento = self._tratarCasComErros(linha_original)
                    if resul_tratamento['sucess']:
                        linhaDf = resul_tratamento['linha']
                    else:
                        listaCAsInvalidos.append(linha_original)
                        continue

                listaCAsValidos.append(linhaDf)

        if listaCAsInvalidos:
            self._criarArquivoComErros(listaCAsInvalidos)

        return listaCAsValidos
    
    def _tratarCasComErros(self, linha) -> dict:
        linhaDf = re.split(r'(?<! )\|', linha)
        if len(linhaDf) > self.nColunas: # Erro
            return {
                'sucess': False,
                'linha': linha
            }

        return    {
            'sucess': True,
            'linha': linhaDf
        }

    def _criarArquivoComErros(self, listaCAsInvalidos:list) -> None:
        with open(self.nomeArquivoErros, 'w') as f:
            f.writelines(listaCAsInvalidos)
    
    def retornarBaseDados(self) -> pd.DataFrame:
        if not os.path.exists(self.nomeArquivoBase):
            print("Aguarde o download...")        
            self._baixarArquivoBaseCaEPI()
            print(f"Download concluido!")

        self._transformarEmDataFrame()
        return self.baseDadosDF

    def inserir_no_banco(self, clear_existing=True) -> int:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clarus.settings")
        import django
        django.setup()

        from django.utils import timezone
        from django_tenants.utils import schema_context
        from apps.caepi.models import CaEPI

        if not self.baseDadosDF:
            self.retornarBaseDados()

        df = self.baseDadosDF.copy()
        df.columns = [str(col).strip() for col in df.columns]
        if "DataValidade" in df.columns:
            df["DataValidade"] = pd.to_datetime(df["DataValidade"], errors="coerce", dayfirst=True).dt.date

        mapping = {
            "RegistroCA": "registro_ca",
            "DataValidade": "data_validade",
            "Situacao": "situacao",
            "NRProcesso": "nr_processo",
            "CNPJ": "cnpj",
            "RazaoSocial": "razao_social",
            "Natureza": "natureza",
            "NomeEquipamento": "nome_equipamento",
            "DescricaoEquipamento": "descricao_equipamento",
            "MarcaCA": "marca_ca",
            "Referencia": "referencia",
            "Cor": "cor",
            "AprovadoParaLaudo": "aprovado_para_laudo",
            "RestricaoLaudo": "restricao_laudo",
            "ObservacaoAnaliseLaudo": "observacao_analise_laudo",
            "CNPJLaboratorio": "cnpj_laboratorio",
            "RazaoSocialLaboratorio": "razao_social_laboratorio",
            "NRLaudo": "nr_laudo",
            "Norma": "norma",
        }
        now = timezone.now()
        def _clean_value(value):
            if pd.isna(value):
                return None
            return value

        objects = []
        for _, row in df.iterrows():
            registro = row.get("RegistroCA")
            if pd.isna(registro) or not str(registro).strip():
                continue
            payload = {
                model_key: _clean_value(row.get(csv_key))
                for csv_key, model_key in mapping.items()
            }
            objects.append(CaEPI(ultima_atualizacao=now, **payload))

        with schema_context("public"):
            if clear_existing:
                CaEPI.objects.all().delete()
            CaEPI.objects.bulk_create(objects, batch_size=2000)

        return len(objects)

def _parse_args():
    parser = argparse.ArgumentParser(description="Importacao CA EPI (public)")
    parser.add_argument("--insert", action="store_true", help="Insere dados no banco public")
    parser.add_argument("--keep-existing", action="store_true", help="Nao limpar registros existentes")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    base = BaseDadosCaEPI()
    if args.insert:
        total = base.inserir_no_banco(clear_existing=not args.keep_existing)
        print(f"Importacao concluida. Registros inseridos: {total}")
    else:
        df = base.retornarBaseDados()
        print(df.head())
