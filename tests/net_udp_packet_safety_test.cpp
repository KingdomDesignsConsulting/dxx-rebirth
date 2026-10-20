#include "net_udp_packet_validate.h"

#include <array>
#include <cassert>
#include <cstdint>
#include <random>
#include <span>
#include <vector>

using namespace dcx::net_udp_validate;

static void put_u32_le(std::vector<std::uint8_t> &v, std::size_t off, std::uint32_t x)
{
	v[off + 0] = static_cast<std::uint8_t>(x);
	v[off + 1] = static_cast<std::uint8_t>(x >> 8);
	v[off + 2] = static_cast<std::uint8_t>(x >> 16);
	v[off + 3] = static_cast<std::uint8_t>(x >> 24);
}

int main()
{
	constexpr std::size_t object_rw_size = 264; // test fixture size; validator is size-parametric
	constexpr std::uint32_t object_none = 0xffffffffu;
	constexpr std::uint32_t checksum = 0xfffffffeu;
	constexpr std::size_t max_objects = 350;
	constexpr std::size_t max_players = 8;

	for (std::size_t n = 0; n < 5; ++n)
		assert(!object_data(std::vector<std::uint8_t>(n), object_rw_size, object_none, checksum, max_objects, max_players));

	{
		std::vector<std::uint8_t> p(5);
		put_u32_le(p, 1, 0xffffffffu); // negative count
		assert(!object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
	}
	{
		std::vector<std::uint8_t> p(5 + 9 + object_rw_size);
		put_u32_le(p, 1, 1);
		put_u32_le(p, 5, 7);
		p[9] = 0;
		put_u32_le(p, 10, 7);
		assert(object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
		p.pop_back();
		assert(!object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
	}
	{
		std::vector<std::uint8_t> p(14);
		put_u32_le(p, 1, 1);
		put_u32_le(p, 5, object_none);
		p[9] = 0;
		assert(object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
		p[9] = 255;
		assert(!object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
	}
	{
		std::vector<std::uint8_t> p(14);
		put_u32_le(p, 1, 1);
		put_u32_le(p, 5, checksum);
		assert(object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
		p.push_back(0);
		assert(!object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
	}
	{
		std::vector<std::uint8_t> p(5 + 9 + object_rw_size);
		put_u32_le(p, 1, 1);
		put_u32_le(p, 5, static_cast<std::uint32_t>(max_objects));
		p[9] = 0;
		assert(!object_data(p, object_rw_size, object_none, checksum, max_objects, max_players));
	}

	constexpr std::size_t endlevel_size = 24;
	{
		std::vector<std::uint8_t> p(endlevel_size);
		p[1] = 7;
		assert(endlevel_client(p, endlevel_size, max_players));
		p[1] = 8;
		assert(!endlevel_client(p, endlevel_size, max_players));
		p.resize(endlevel_size - 1);
		assert(!endlevel_client(p, endlevel_size, max_players));
	}

	/* Sanitizer-backed randomized malformed input sweep.  Acceptance is allowed
	 * only if the random bytes happen to form a structurally valid datagram; the
	 * purpose here is to exercise every bounds computation without OOB/UB. */
	std::mt19937_64 rng(0x4458585245424952ULL);
	std::uniform_int_distribution<std::size_t> length_dist(0, 2048);
	std::uniform_int_distribution<unsigned> byte_dist(0, 255);
	for (unsigned iteration = 0; iteration < 250000; ++iteration)
	{
		std::vector<std::uint8_t> p(length_dist(rng));
		for (auto &b : p)
			b = static_cast<std::uint8_t>(byte_dist(rng));
		(void)object_data(p, object_rw_size, object_none, checksum, max_objects, max_players);
		(void)endlevel_client(p, endlevel_size, max_players);
	}
}
