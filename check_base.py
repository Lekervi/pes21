import json
import os

def audit_pes_database():
    file_path = 'history.json'
    
    if not os.path.exists(file_path):
        print(f"❌ Ошибка: Файл {file_path} не найден в текущей папке!")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"❌ Ошибка чтения JSON: {e}")
            return

    print(f"📊 Всего матчей в базе: {len(data)}")
    print("="*60)

    seen_stats = []
    
    for idx, match in enumerate(data):
        match_id = idx + 1
        t1 = match.get('team_1', {})
        t2 = match.get('team_2', {})
        
        g1 = t1.get('goals', 0)
        g2 = t2.get('goals', 0)
        
        s1 = t1.get('scorers', [])
        s2 = t2.get('scorers', [])
        
        st1 = t1.get('stats', {})
        st2 = t2.get('stats', {})

        # 1. Проверка на пустые списки авторов при наличии голов
        if g1 > 0 and not s1:
            print(f"⚠️ МАТЧ #{match_id} ({g1}:{g2}): У Германии есть голы ({g1}), но список авторов ПУСТ!")
        if g2 > 0 and not s2:
            print(f"⚠️ МАТЧ #{match_id} ({g1}:{g2}): У Испании есть голы ({g2}), но список авторов ПУСТ!")

        # 2. Проверка соответствия количества голов и авторов (с учетом лимита в 3 имени из-за прокрутки)
        if s1 and len(s1) != g1:
            # Считаем автоголы, которые Испания забила сама себе в пользу Германии
            og_count = sum(1 for goal in s2 if goal.get('type') == 'own_goal')
            
            # Если голов больше 3 и в списке ровно 3 автора (лимит интерфейса) — это НОРМА, не ругаемся
            if g1 > 3 and len(s1) == 3:
                pass
            # Во всех остальных случаях проверяем жестко
            elif len(s1) + og_count != g1:
                print(f"❓ МАТЧ #{match_id} ({g1}:{g2}): У Германии счет {g1}, но в списке авторов указано {len(s1)} гол(ов).")
                
        if s2 and len(s2) != g2:
            # Считаем автоголы, которые Германия забила сама себе в пользу Испании
            og_count = sum(1 for goal in s1 if goal.get('type') == 'own_goal')
            
            # Если голов больше 3 и в списке ровно 3 автора (лимит интерфейса) — это НОРМА, не ругаемся
            if g2 > 3 and len(s2) == 3:
                pass
            # Во всех остальных случаях проверяем жестко
            elif len(s2) + og_count != g2:
                print(f"❓ МАТЧ #{match_id} ({g1}:{g2}): У Испании счет {g2}, но в списке авторов указано {len(s2)} гол(ов).")

        # 3. Проверка на полные клоны по статистике
        if st1 and st2:
            current_fingerprint = (
                st1.get('possession_pct'), st1.get('shots'), st1.get('shots_on_target'),
                st1.get('total_passes'), st1.get('successful_passes'),
                st2.get('possession_pct'), st2.get('shots'), st2.get('shots_on_target')
            )
            
            if current_fingerprint in seen_stats:
                print(f"🚨 МАТЧ #{match_id} ({g1}:{g2}) дублирует статистику одного из предыдущих матчей! (Возможный клон скриншота)")
            else:
                seen_stats.append(current_fingerprint)

        # 4. Проверка на логические аномалии в статистике
        if st1:
            if st1.get('shots_on_target', 0) > st1.get('shots', 0):
                print(f"💥 МАТЧ #{match_id}: У Германии ударов в створ больше, чем всего ударов!")
            if st1.get('successful_passes', 0) > st1.get('total_passes', 0):
                print(f"💥 МАТЧ #{match_id}: У Германии точных пасов больше, чем всего пасов!")
                
        if st2:
            if st2.get('shots_on_target', 0) > st2.get('shots', 0):
                print(f"💥 МАТЧ #{match_id}: У Испании ударов в створ больше, чем всего ударов!")
            if st2.get('successful_passes', 0) > st2.get('total_passes', 0):
                print(f"💥 МАТЧ #{match_id}: У Испании точных пасов больше, чем всего пасов!")

    print("="*60)
    print("🔍 Аудит завершен.")

if __name__ == "__main__":
    audit_pes_database()