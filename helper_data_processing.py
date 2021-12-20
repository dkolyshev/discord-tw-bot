import twitter_api
import helper_db
from discord import Embed

async def dtw_check_processing(ctx, accs, send_msg_if_nothing=True):
    for acc in accs:
        ids = await twitter_api.get_followers_ids(acc)
        new_follow = await check_flws_toadd(acc, ids)
        # now we need to check if some of follows were removed
        follows_to_remove = await check_flws_toremove(acc, ids)

        embed_msg = []
        if len(follows_to_remove) > 0:
            print("The follows IDs that were unfollowed:")
            print(follows_to_remove)
            embed_msg_follows_to_remove = Embed(title="Updates!", description="The account **" + acc + "** unfollowed: ", color=0xff0000)
            total_follows_to_remove = len(follows_to_remove)
            for i in range(total_follows_to_remove):
                helper_db.conn.execute("DELETE FROM tw_accs_data WHERE friend_id = ?", (follows_to_remove[i],))
                helper_db.conn.commit()
                follow_to_remove_name = await twitter_api.get_user_name(follows_to_remove[i])
                if follow_to_remove_name:
                    embed_msg_follows_to_remove.add_field(name=follow_to_remove_name, value="https://twitter.com/" + follow_to_remove_name, inline=True)
                else:
                    embed_msg_follows_to_remove.add_field(name=follows_to_remove[i], value="Account was suspended", inline=True)
            embed_msg.append(embed_msg_follows_to_remove)
        
        if len(new_follow) > 0:
            embed_msg_new_follows = Embed(title="Updates!", description="The account **" + acc + "** started following: ", color=0x00ff00)
            total_new_followers = len(new_follow)
            for i in range(total_new_followers):
                new_follow_name = await twitter_api.get_user_name(new_follow[i])
                if new_follow_name:
                    embed_msg_new_follows.add_field(name=new_follow_name, value="https://twitter.com/" + new_follow_name, inline=True)
            embed_msg.append(embed_msg_new_follows)
        
        if len(embed_msg) > 0:
            for msg in embed_msg:
                await ctx.send(embed=msg) 
        elif send_msg_if_nothing:
            await ctx.send("No updates for " + acc)

async def check_flws_toremove(acc, ids):
    follows_to_remove = []
    existing_follows_raw = helper_db.conn.execute("SELECT friend_id FROM tw_accs_data WHERE account_name = ?", (acc,))
    if existing_follows_raw != None:
        existing_follows = list(existing_follows_raw)
        for existing_id in existing_follows:
            if existing_id[0] not in ids:
                follows_to_remove.append(existing_id[0])
    else:
        print("Acc name: " + acc)
        print(existing_follows_raw)
    return follows_to_remove

async def check_flws_toadd(acc, ids):
    # Check of followers for screen name (acc) exists in DB
    print("Starting to parse data for account name " + acc)
    account_name_exist = helper_db.db_record_exists(helper_db.conn, 'tw_accs_data', 'account_name', acc)
    new_follow = []
    if account_name_exist:
        print("Found account " + acc + " in DB.")
    else:
        print("Account " + acc + " not found in DB.")
    
    print("Total amount of friends is " + str(len(ids)))
    for id in ids:
        lid = helper_db.get_last_id(helper_db.conn, 'tw_accs_data')
        user_exists = helper_db.db_record_exists(helper_db.conn, 'tw_accs_data', 'friend_id', id)
        if user_exists == False:
            helper_db.db_execute_query(helper_db.conn, "INSERT INTO tw_accs_data (id,account_name,friend_id) VALUES (?, ?, ?)", (lid, acc, id))
            if new_follow != False:
                new_follow.append(id)
    if new_follow:
        print("New follows IDs:")
        print(new_follow)
    
    return new_follow