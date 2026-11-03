import pytest

HEADER_EXP = "CO_ANO;CO_MES;CO_NCM;CO_UNID;CO_PAIS;SG_UF_NCM;CO_VIA;CO_URF;QT_ESTAT;KG_LIQUIDO;VL_FOB"
HEADER_IMP = HEADER_EXP + ";VL_FRETE;VL_SEGURO"


def escrever(path, header, linhas):
    path.write_text("\n".join([header, *linhas]) + "\n", encoding="latin-1")
    return path


@pytest.fixture
def exp_2017(tmp_path):
    return escrever(tmp_path / "EXP_2017.csv", HEADER_EXP, [
        '2017;01;"02013000";10;160;"SP";01;0817600;10;1000;5000',
        '2017;01;"02013000";10;249;"SP";01;0817600;5;500;2500',   # mesma chave -> agregada
        '2017;02;"9011000";10;160;"MT";01;0817600;1;100;700',      # NCM sem zero à esquerda
        '2017;12;"10059010";10;160;"PR";01;0817600;1;100;300',
    ])


@pytest.fixture
def imp_2017(tmp_path):
    return escrever(tmp_path / "IMP_2017.csv", HEADER_IMP, [
        '2017;03;"84713012";11;249;"SC";01;0927800;2;5;1200;10;1',
        '2017;03;"84713012";11;249;"AM";04;0817600;2;5;800;10;1',
    ])
