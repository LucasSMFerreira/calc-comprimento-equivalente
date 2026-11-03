# Validação

| Caso | Esperado | Calculadora | Observação |
| --- | --- | --- | --- |
| Exercício 5 (3/4", PVC + registro Metal) | 17,80 m | 17,80 m | Igual. Teste automático `test_exercicio_5_dos_slides_da_17_80` |
| Joelho 90° PVC 3/4" | 1,2 m (slide) | 1,20 m | Igual |
| Exemplo do slide 46 (Metal 1") | 30,8 m | 23,08 m | O slide usa uma tabela antiga (joelho 90° metal 1" = 0,8; na planilha, 0,94) e o valor 8,2 é o do registro de globo. Trocando gaveta por globo, dá 31,08 m |

## Valores da planilha sinalizados para conferência

O importador avisa quando um valor é menor que o do diâmetro anterior:

- Curva de Transposição (Metal) 1/2" = 0,87 m (célula F21), maior que 3/4" = 0,48 m
- Luva de Redução (PVC e Metal) de 3/4" a 1 1/2": valores diminuem
- Niple de Redução (Metal) de 3/4" a 6": valores de 0,01 a 0,03 m