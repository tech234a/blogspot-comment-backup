import asyncio, aiohttp

GET_ID_ENDPOINT = "https://blogspot-comments-master.herokuapp.com/worker/getID"
# worker id must be provided as a query parameter: id={ID}
GET_BATCH_ENDPOINT = "https://blogspot-comments-master.herokuapp.com/worker/getBatch"


async def get_worker_id(session):
	response = await session.get(GET_ID_ENDPOINT)
	if response.status == 200:
		text = await response.text()
		return text
	else:
		print(f"The server response was unsucessful ({response.status}), unable to get a worker ID")

async def get_batch(worker_id, session):
	params = {"id": worker_id}
	response = await session.get(GET_BATCH_ENDPOINT, params=params)
	if response.status == 200:
		obj = json.loads(await response.text())
		return {"batch_id": obj.batchId, "random_key": obj.randomKey}
	else:
		print(f"The server response was unsucessful ({response.status}), unable to get a batch")


async def main():
	async with aiohttp.ClientSession() as session:
		# server isn't working reliably right now, will test with the actual server later
		worker_id = await get_worker_id(session)
		# worker_id = "27747438-9825-51e1-9578-8807297944e6"
		if worker_id:
			batch = await get_batch(worker_id, session)
		else:
			print("worker_id is not set")

if __name__ == '__main__':
	asyncio.run(main())